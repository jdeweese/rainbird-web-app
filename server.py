#!/usr/bin/env python3
"""
RainBird Web App Server — server-authoritative irrigation control for ESP-ME3.

Architecture
------------
A single background thread (IrrigationManager) owns ALL controller I/O. It runs
one long-lived asyncio event loop, so a persistent aiohttp session/controller can
be reused safely (the old per-request-event-loop design could not reuse sessions,
which is why stop/adjust commands used to hang).

The manager holds the authoritative state:
  - a queue of watering jobs (the head, if running, is the active zone)
  - rain sensor state and controller-online status
  - a monotonically increasing `version` bumped on every change

HTTP request handlers (served by a ThreadingHTTPServer, so many clients are handled
concurrently) NEVER touch the controller directly. They only mutate desired state
under a lock and notify; the manager's reconcile loop drives the controller to match.

Multi-client sync is done with long-polling: GET /api/state?since=<version> blocks
until the version changes (or a timeout), so every connected browser updates within
a second of any change from any client.

ESP-ME3 reality: one zone at a time, manual control only (no stored programs), whole
-minute durations. The "queue" is implemented entirely server-side on top of single
-zone control — jobs run sequentially, head first.
"""

import json
import os
import math
import uuid
import asyncio
import threading
import aiohttp
import socket
import ipaddress
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pyrainbird import async_client

# Config lives next to this script by default; Docker overrides via CONFIG_PATH.
_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.json")


def config_path():
    return os.environ.get("CONFIG_PATH", _DEFAULT_CONFIG_PATH)


def state_path():
    # Keep state.json beside config.json so it survives container recreation
    # (the config dir is the mounted volume).
    return os.environ.get("STATE_PATH", os.path.join(os.path.dirname(config_path()), "state.json"))


def load_settings():
    try:
        with open(config_path(), "r") as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}
    settings.setdefault("controller_ip", "")
    settings.setdefault("controller_password", "")
    settings.setdefault("timeout", 10)
    settings.setdefault("refresh_interval", 5)
    settings.setdefault("zone_names", {})
    settings.setdefault("visible_zones", [])
    return settings


def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


# Duration sanity bounds (minutes)
MIN_MINUTES = 1
MAX_MINUTES = 600


class IrrigationManager:
    """Owns controller I/O and the authoritative irrigation state.

    Public methods are called from HTTP handler threads and only mutate state
    under the lock. The background reconcile loop is the sole caller of the
    pyrainbird controller.
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.state = {
            "queue": [],              # list of job dicts (see _new_job)
            "rain_sensor": False,
            "controller_online": False,
            "controller_configured": False,
            "version": 1,
            "updated_at": time.time(),
        }
        self.actual_zone = None       # zone we believe the controller is running
        self._settings_key = None
        self.session = None
        self.controller = None
        self.loop = asyncio.new_event_loop()
        self._load_state()
        threading.Thread(target=self._thread_main, daemon=True).start()

    # ────────────────────────── persistence ──────────────────────────
    def _load_state(self):
        try:
            with open(state_path(), "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        now = time.time()
        queue = []
        for job in data.get("queue", []):
            if job.get("state") == "running":
                # Resume after a restart: if its time already passed, drop it;
                # otherwise force the reconciler to re-issue the controller command.
                if job.get("ends_at") and job["ends_at"] <= now:
                    continue
                job["restart_requested"] = True
            queue.append(job)
        self.state["queue"] = queue

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(state_path()), exist_ok=True)
            with open(state_path(), "w") as f:
                json.dump({"queue": self.state["queue"]}, f)
        except Exception:
            pass

    # ────────────────────────── helpers ──────────────────────────
    def _new_job(self, zone_id, duration_min):
        minutes = max(MIN_MINUTES, min(MAX_MINUTES, int(duration_min)))
        return {
            "id": uuid.uuid4().hex[:8],
            "zone_id": int(zone_id),
            "duration_sec": minutes * 60,
            "state": "pending",        # pending | running
            "ends_at": None,
            "restart_requested": False,
        }

    def _bump(self):
        self.state["version"] += 1
        self.state["updated_at"] = time.time()
        self._persist()
        self.cond.notify_all()

    def _update_job(self, job_id, **fields):
        for job in self.state["queue"]:
            if job["id"] == job_id:
                job.update(fields)
                return True
        return False

    def _set_online(self, online):
        with self.lock:
            if self.state["controller_online"] != bool(online):
                self.state["controller_online"] = bool(online)
                self._bump()

    def _public_state(self):
        now = time.time()
        names = load_settings().get("zone_names", {})
        queue = []
        for job in self.state["queue"]:
            item = {
                "id": job["id"],
                "zone_id": job["zone_id"],
                "name": names.get(str(job["zone_id"]), f"Zone {job['zone_id']}"),
                "duration_sec": job["duration_sec"],
                "state": job["state"],
            }
            if job["state"] == "running" and job.get("ends_at"):
                item["remaining_sec"] = max(0, int(round(job["ends_at"] - now)))
                item["ends_at"] = job["ends_at"]
            queue.append(item)
        return {
            "version": self.state["version"],
            "queue": queue,
            "rain_sensor": self.state["rain_sensor"],
            "controller_online": self.state["controller_online"],
            "controller_configured": self.state["controller_configured"],
            "server_time": now,
        }

    # ────────────────────────── public API (HTTP threads) ──────────────────────────
    def snapshot(self):
        with self.lock:
            return self._public_state()

    def wait_for_change(self, since_version, timeout=25):
        with self.lock:
            if self.state["version"] != since_version:
                return self._public_state()
            self.cond.wait(timeout)
            return self._public_state()

    def add(self, zone_id, duration_min):
        with self.lock:
            self.state["queue"].append(self._new_job(zone_id, duration_min))
            self._bump()

    def run_now(self, zone_id, duration_min):
        with self.lock:
            q = self.state["queue"]
            if q and q[0]["state"] == "running":
                q.pop(0)  # reconciler will stop the controller and start the new head
            q.insert(0, self._new_job(zone_id, duration_min))
            self._bump()

    def remove(self, job_id):
        with self.lock:
            self.state["queue"] = [j for j in self.state["queue"] if j["id"] != job_id]
            self._bump()

    def reorder(self, ids):
        with self.lock:
            by_id = {j["id"]: j for j in self.state["queue"]}
            new_q = [by_id[i] for i in ids if i in by_id]
            for j in self.state["queue"]:  # append any not mentioned
                if j not in new_q:
                    new_q.append(j)
            # A running job must stay at the head — never demote what's watering.
            running = [j for j in new_q if j["state"] == "running"]
            if running:
                new_q.remove(running[0])
                new_q.insert(0, running[0])
            self.state["queue"] = new_q
            self._bump()

    def edit(self, job_id, duration_min):
        minutes = max(MIN_MINUTES, min(MAX_MINUTES, int(duration_min)))
        with self.lock:
            for job in self.state["queue"]:
                if job["id"] == job_id:
                    if job["state"] == "running":
                        job["ends_at"] = time.time() + minutes * 60
                        job["restart_requested"] = True
                    job["duration_sec"] = minutes * 60
                    self._bump()
                    break

    def adjust(self, delta_min):
        with self.lock:
            q = self.state["queue"]
            if q and q[0]["state"] == "running":
                job = q[0]
                base = job.get("ends_at") or time.time()
                job["ends_at"] = max(time.time() + 5, base + delta_min * 60)
                job["duration_sec"] = max(60, job["duration_sec"] + delta_min * 60)
                job["restart_requested"] = True
                self._bump()

    def stop_current(self):
        with self.lock:
            if self.state["queue"]:
                self.state["queue"].pop(0)
                self._bump()

    def stop_all(self):
        with self.lock:
            self.state["queue"] = []
            self._bump()

    # ────────────────────────── background loop ──────────────────────────
    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._scheduler())

    async def _scheduler(self):
        last_poll = 0.0
        while True:
            try:
                await self._ensure_controller()
                await self._reconcile()
                if time.time() - last_poll > 8:
                    await self._poll_controller()
                    last_poll = time.time()
            except Exception:
                self._set_online(False)
            await asyncio.sleep(1)

    async def _ensure_controller(self):
        s = load_settings()
        ip, pw = s.get("controller_ip"), s.get("controller_password")
        configured = bool(ip and pw)
        with self.lock:
            if self.state["controller_configured"] != configured:
                self.state["controller_configured"] = configured
                self._bump()
        if not configured:
            self.controller = None
            self._settings_key = None
            return
        key = f"{ip}:{pw}"
        if key != self._settings_key:
            if self.session:
                try:
                    await self.session.close()
                except Exception:
                    pass
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            self.controller = async_client.CreateController(self.session, ip, pw)
            self._settings_key = key
            self.actual_zone = None

    async def _reconcile(self):
        now = time.time()
        # 1) Expire a finished running head.
        with self.lock:
            q = self.state["queue"]
            if q and q[0]["state"] == "running" and q[0].get("ends_at") and now >= q[0]["ends_at"] - 0.5:
                q.pop(0)
                self.actual_zone = None
                self._bump()
            head = dict(q[0]) if q else None   # read-only copy
            actual = self.actual_zone

        if not self.controller:
            return

        try:
            # 2) Wrong zone running → stop it.
            if actual is not None and (head is None or head["zone_id"] != actual):
                await self.controller.stop_irrigation()
                with self.lock:
                    self.actual_zone = None
                actual = None

            if head is None:
                self._set_online(True)
                return

            # 3) Start a pending head.
            if head["state"] == "pending":
                minutes = max(1, math.ceil(head["duration_sec"] / 60))
                await self.controller.irrigate_zone(head["zone_id"], minutes)
                with self.lock:
                    self._update_job(head["id"], state="running",
                                     ends_at=time.time() + head["duration_sec"],
                                     restart_requested=False)
                    self.actual_zone = head["zone_id"]
                    self._bump()

            # 4) Restart a running head after an adjust/edit.
            elif head["state"] == "running" and head.get("restart_requested"):
                remaining = max(1, math.ceil((head["ends_at"] - time.time()) / 60))
                await self.controller.stop_irrigation()
                await asyncio.sleep(1)
                await self.controller.irrigate_zone(head["zone_id"], remaining)
                with self.lock:
                    self._update_job(head["id"], restart_requested=False)
                    self.actual_zone = head["zone_id"]
                    self._bump()
            else:
                with self.lock:
                    self.actual_zone = head["zone_id"]

            self._set_online(True)
        except Exception:
            self._set_online(False)

    async def _poll_controller(self):
        if not self.controller:
            self._set_online(False)
            return
        try:
            rain = await self.controller.get_rain_sensor_state()
            with self.lock:
                if self.state["rain_sensor"] != bool(rain):
                    self.state["rain_sensor"] = bool(rain)
                    self._bump()
            self._set_online(True)
        except Exception:
            self._set_online(False)


# Single global manager instance.
MANAGER = IrrigationManager()


class RainBirdHandler(BaseHTTPRequestHandler):

    # ────────────────────────── routing ──────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.serve_file("index.html")
        elif path == "/api/zones":
            self.handle_get_zones()
        elif path == "/api/state":
            self.handle_get_state(parse_qs(parsed.query))
        elif path == "/api/scan":
            self.handle_scan()
        elif path.startswith("/"):
            self.serve_file(path[1:])
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        routes = {
            "/api/queue/add":      self._q_add,
            "/api/queue/run-now":  self._q_run_now,
            "/api/queue/remove":   self._q_remove,
            "/api/queue/reorder":  self._q_reorder,
            "/api/queue/edit":     self._q_edit,
            "/api/queue/adjust":   self._q_adjust,
            "/api/queue/stop":     self._q_stop,
            "/api/queue/stop-all": self._q_stop_all,
            "/api/settings":       lambda b: self.handle_settings(b),
        }
        fn = routes.get(path)
        if not fn:
            self.send_error(404)
            return
        try:
            fn(body)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    # ────────────────────────── queue endpoints ──────────────────────────
    def _q_add(self, b):
        MANAGER.add(int(b["zone_id"]), int(b["duration_min"]))
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_run_now(self, b):
        MANAGER.run_now(int(b["zone_id"]), int(b["duration_min"]))
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_remove(self, b):
        MANAGER.remove(b["id"])
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_reorder(self, b):
        MANAGER.reorder(b["ids"])
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_edit(self, b):
        MANAGER.edit(b["id"], int(b["duration_min"]))
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_adjust(self, b):
        MANAGER.adjust(int(b["delta_min"]))
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_stop(self, b):
        MANAGER.stop_current()
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    def _q_stop_all(self, b):
        MANAGER.stop_all()
        self.send_json_response({"success": True, "state": MANAGER.snapshot()})

    # ────────────────────────── state / zones ──────────────────────────
    def handle_get_state(self, query):
        since = query.get("since", [None])[0]
        if since is not None:
            try:
                state = MANAGER.wait_for_change(int(since), timeout=25)
            except ValueError:
                state = MANAGER.snapshot()
        else:
            state = MANAGER.snapshot()
        self.send_json_response({"success": True, "state": state})

    def handle_get_zones(self):
        settings = load_settings()
        names = settings.get("zone_names", {})
        visible = settings.get("visible_zones", [])
        zones = []
        for zid in range(1, 20):
            zones.append({
                "id": zid,
                "name": names.get(str(zid), f"Zone {zid}"),
                "visible": (not visible) or (zid in visible),
            })
        self.send_json_response({"success": True, "zones": zones,
                                 "visible_zones": visible})

    # ────────────────────────── settings ──────────────────────────
    def handle_settings(self, body):
        action = body.get("action")
        if action == "load":
            self.send_json_response({"success": True, "settings": load_settings()})
        elif action == "save":
            incoming = body.get("settings", {})
            merged = load_settings()
            merged.update(incoming)
            self.send_json_response({"success": save_settings(merged)})
        elif action == "update-zone-name":
            settings = load_settings()
            settings.setdefault("zone_names", {})[str(body.get("zone_id"))] = body.get("name")
            ok = save_settings(settings)
            # Names changed → push a state bump so all clients re-render labels.
            with MANAGER.lock:
                MANAGER._bump()
            self.send_json_response({"success": ok})
        else:
            self.send_error(400, "Invalid action")

    # ────────────────────────── LAN scan ──────────────────────────
    def handle_scan(self):
        try:
            self.send_json_response({"success": True, "controllers": self._scan_for_controllers()})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e), "controllers": []})

    def _scan_for_controllers(self):
        subnet = self._get_local_subnet()
        if not subnet:
            return []
        hosts = [str(h) for h in ipaddress.IPv4Network(subnet, strict=False).hosts()]
        with ThreadPoolExecutor(max_workers=64) as pool:
            reachable = pool.map(self._tcp_probe, hosts)
        return [ip for ip, ok in zip(hosts, reachable) if ok]

    def _get_local_subnet(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return str(ipaddress.IPv4Network(f"{local_ip}/24", strict=False))
        except Exception:
            return None

    def _tcp_probe(self, ip, port=80, timeout=0.4):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except Exception:
            return False

    # ────────────────────────── static files / utils ──────────────────────────
    def serve_file(self, filename):
        try:
            with open(filename, "rb") as f:
                content = f.read()
            if filename.endswith(".html"):
                ctype = "text/html"
            elif filename.endswith(".css"):
                ctype = "text/css"
            elif filename.endswith(".js"):
                ctype = "application/javascript"
            else:
                ctype = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def send_json_response(self, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass  # client navigated away mid long-poll

    def log_message(self, fmt, *args):
        pass  # quiet


def run_server(port=8000):
    server = ThreadingHTTPServer(("0.0.0.0", port), RainBirdHandler)
    server.daemon_threads = True
    print(f"🌱 RainBird server running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
