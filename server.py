#!/usr/bin/env python3
"""
RainBird Web App Server — server-authoritative irrigation control for ESP-ME3.

See docs/architecture.html for the full illustrated design. Summary below.

The problem
-----------
The ESP-ME3 is a hostile I/O target:
  * It accepts ONE TCP connection at a time and resets/refuses concurrent ones.
  * Its port 80 is intermittent — it goes unresponsive between internal cycles.
  * Reads are unreliable: get_current_irrigation/get_rain_sensor often time out.
  * Therefore we treat the controller as essentially WRITE-ONLY and never rely
    on reading authoritative state back from it.

The design: server owns state, single worker drives the device
--------------------------------------------------------------
1. STATE lives on the server (the watering queue + derived timers). It is the
   single source of truth. The head of the queue is the job that SHOULD be
   watering. Clients never talk to the controller; they only edit server state.

2. A single background WORKER thread owns the one allowed controller connection
   and runs a level-triggered reconcile loop: compare "what the controller
   should be doing" (head of queue) against "what we last successfully told it"
   (`applied`). When they differ it computes ONE command (start zone X X min, or
   stop) and tries to apply it.

3. RETRIES use capped exponential backoff with jitter. A failed command (or a
   failed connection) schedules the next attempt at delay = min(MAX, BASE*2^n)
   ± jitter, growing 1s → 2s → 4s → … → 30s, so we don't hammer a busy device.
   A success resets the backoff to zero.

4. TIMING: the head's countdown (`ends_at`) starts only once its start command
   is CONFIRMED applied — so the timer reflects reality, not optimism. When the
   countdown reaches zero the worker advances the queue and the next head becomes
   the new target. Editing/adjusting the head re-targets and re-applies.

5. MULTI-CLIENT SYNC: every state change bumps a monotonic `version` and wakes
   long-pollers. GET /api/state?since=<v> blocks until version != v, so all
   browsers converge within ~1s of any change from any client (or the worker).

HTTP is served by ThreadingHTTPServer; handlers only mutate state under a lock
and notify. The worker is the sole caller of pyrainbird.
"""

import json
import os
import math
import uuid
import random
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
    settings.setdefault("zone_order", [])
    settings.setdefault("shortcuts", [])   # [{zone_id, minutes}]
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

# Exponential-backoff retry policy for controller commands (seconds).
BACKOFF_BASE = 1.0      # first retry delay
BACKOFF_MAX = 30.0      # cap
BACKOFF_JITTER = 0.3    # ±30% randomization to avoid lockstep retries
CMD_TIMEOUT = 8.0       # per-command controller timeout
POLL_INTERVAL = 15.0    # idle liveness-probe interval (drives connection status)


async def _probe_rainbird(ip, password, timeout=6):
    """Try a real RainBird protocol handshake against ip.

    Returns a dict describing the result:
      {"ip", "controllable": bool, "model": str|None, "reason": str}
    - controllable True  → device decrypted our request and returned a model;
      it's a genuine, talk-able controller with this password.
    - controllable False → reason explains why (auth failed, no protocol, timeout).
    """
    result = {"ip": ip, "controllable": False, "model": None, "reason": ""}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
            controller = async_client.CreateController(s, ip, password or "")
            mv = await controller.get_model_and_version()
            result["controllable"] = True
            # mv has .model (code) and a friendly name on some lib versions
            model = getattr(mv, "model", None)
            name = getattr(mv, "model_name", None) or model
            result["model"] = str(name) if name else "RainBird"
            result["reason"] = "handshake ok"
    except Exception as e:
        cls = type(e).__name__
        if "Auth" in cls:
            # Spoke the protocol but the password was wrong → it IS a controller.
            result["reason"] = "wrong password"
            result["is_controller"] = True
        else:
            result["reason"] = cls
    return result


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
            "queue": [],              # desired state: list of job dicts (_new_job)
            "rain_sensor": False,
            "controller_online": False,
            "controller_configured": False,
            "controller_state": "idle",  # idle|connecting|watering|retrying|offline
            "last_error": None,          # human-readable last controller error
            "next_retry_at": None,       # epoch of next scheduled attempt (if retrying)
            "version": 1,
            "updated_at": time.time(),
        }
        # `applied` = what we have CONFIRMED the controller is doing:
        #   None            → controller is stopped (or we believe so)
        #   (job_id, zone)  → controller was told to water this job's zone
        self.applied = None
        self._fail_streak = 0         # consecutive failures (online hysteresis)
        self._backoff_n = 0           # current backoff exponent
        self._next_attempt = 0.0      # epoch; worker waits until this to retry
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
            # Drop a head whose time already elapsed while we were down.
            if job.get("ends_at") and job["ends_at"] <= now:
                continue
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
    # Model: the queue is the single source of truth. The head is what SHOULD be
    # watering. The worker tracks `applied` (what it has CONFIRMED the controller
    # is doing) separately, and only sets a job's countdown (`ends_at`) once its
    # start command is confirmed — so the timer reflects reality. A flaky/offline
    # controller leaves the head "starting" (no countdown) and is retried with
    # exponential backoff; it never freezes the queue or the UI for other clients.
    def _new_job(self, zone_id, duration_min):
        minutes = max(MIN_MINUTES, min(MAX_MINUTES, int(duration_min)))
        return {
            "id": uuid.uuid4().hex[:8],
            "zone_id": int(zone_id),
            "duration_sec": minutes * 60,
            "ends_at": None,           # set once the worker confirms the start command
        }

    def _clear_nonhead_timers(self):
        """Only the head may have a running countdown. Any non-head job gets its
        ends_at cleared so a demoted job restarts cleanly if it returns to the
        head. The head's countdown is NOT started here — it begins only once the
        reconciler has successfully pushed the job to the controller. Must be
        called with the lock held."""
        for i, job in enumerate(self.state["queue"]):
            if i != 0 and job.get("ends_at") is not None:
                job["ends_at"] = None

    def _bump(self):
        self._clear_nonhead_timers()
        self.state["version"] += 1
        self.state["updated_at"] = time.time()
        self._persist()
        self.cond.notify_all()

    def _retarget(self):
        """Force the worker to re-apply the head on its next tick by forgetting
        what we believe the controller is doing, and reset backoff so the retry
        happens promptly. Must hold the lock."""
        self.applied = None
        self._backoff_n = 0
        self._next_attempt = 0.0

    def _schedule_retry(self, err):
        """Arm capped exponential backoff after a failed controller command.
        Must hold the lock."""
        delay = min(BACKOFF_MAX, BACKOFF_BASE * (2 ** self._backoff_n))
        delay *= 1 + random.uniform(-BACKOFF_JITTER, BACKOFF_JITTER)
        self._backoff_n = min(self._backoff_n + 1, 10)
        self._next_attempt = time.time() + delay
        self.state["next_retry_at"] = self._next_attempt
        self.state["last_error"] = str(err)[:200] if err else None

    def _clear_backoff(self):
        """Reset backoff after a successful command. Must hold the lock."""
        self._backoff_n = 0
        self._next_attempt = 0.0
        if self.state["next_retry_at"] is not None:
            self.state["next_retry_at"] = None

    def _update_job(self, job_id, **fields):
        for job in self.state["queue"]:
            if job["id"] == job_id:
                job.update(fields)
                return True
        return False

    def _set_online(self, online):
        """Update online status with hysteresis to stop UI flapping.

        The ESP-ME3 handles one connection at a time and throws transient errors
        often, so a single failure shouldn't flip us to "offline". Go online
        immediately on any success; only declare offline after OFFLINE_STREAK
        consecutive failures.
        """
        OFFLINE_STREAK = 3
        with self.lock:
            if online:
                self._fail_streak = 0
                if not self.state["controller_online"]:
                    self.state["controller_online"] = True
                    self.state["last_error"] = None
                    self._bump()
            else:
                self._fail_streak = self._fail_streak + 1
                if self._fail_streak >= OFFLINE_STREAK and self.state["controller_online"]:
                    self.state["controller_online"] = False
                    self._bump()

    def _set_ctrl_state(self, label):
        """Set the coarse controller_state shown to clients. Must hold the lock."""
        if self.state["controller_state"] != label:
            self.state["controller_state"] = label
            self._bump()

    def _public_state(self):
        now = time.time()
        names = load_settings().get("zone_names", {})
        queue = []
        for i, job in enumerate(self.state["queue"]):
            is_head = (i == 0)
            # Head is "running" once its countdown has started (controller
            # accepted it), otherwise "starting" (waiting on the controller).
            if is_head:
                head_state = "running" if job.get("ends_at") else "starting"
            else:
                head_state = "pending"
            item = {
                "id": job["id"],
                "zone_id": job["zone_id"],
                "name": names.get(str(job["zone_id"]), f"Zone {job['zone_id']}"),
                "duration_sec": job["duration_sec"],
                "state": head_state,
            }
            if is_head and job.get("ends_at"):
                item["remaining_sec"] = max(0, int(round(job["ends_at"] - now)))
                item["ends_at"] = job["ends_at"]
            queue.append(item)
        return {
            "version": self.state["version"],
            "queue": queue,
            "rain_sensor": self.state["rain_sensor"],
            "controller_online": self.state["controller_online"],
            "controller_configured": self.state["controller_configured"],
            "controller_state": self.state["controller_state"],
            "last_error": self.state["last_error"],
            "next_retry_at": self.state["next_retry_at"],
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
        """Add to the end of the queue (or start it running if queue was empty)."""
        with self.lock:
            self.state["queue"].append(self._new_job(zone_id, duration_min))
            self._bump()

    def add_many(self, items):
        """Append several jobs at once. items = [{zone_id, duration_min}, ...].
        One bump → one state push, so the queue updates atomically for all clients."""
        with self.lock:
            for it in items:
                self.state["queue"].append(self._new_job(it["zone_id"], it["duration_min"]))
            self._bump()

    def run_now(self, zone_id, duration_min):
        """Insert at the head so it runs immediately, preempting whatever's running."""
        with self.lock:
            self.state["queue"].insert(0, self._new_job(zone_id, duration_min))
            self._bump()

    def remove(self, job_id):
        with self.lock:
            self.state["queue"] = [j for j in self.state["queue"] if j["id"] != job_id]
            self._bump()

    def reorder(self, ids):
        """Set queue order from a full list of ids. The new head becomes what runs —
        if it differs from the current head, the reconciler re-pushes it."""
        with self.lock:
            by_id = {j["id"]: j for j in self.state["queue"]}
            new_q = [by_id[i] for i in ids if i in by_id]
            for j in self.state["queue"]:  # append any not mentioned (safety)
                if j not in new_q:
                    new_q.append(j)
            self.state["queue"] = new_q
            self._bump()

    def edit(self, job_id, duration_min):
        minutes = max(MIN_MINUTES, min(MAX_MINUTES, int(duration_min)))
        with self.lock:
            q = self.state["queue"]
            for i, job in enumerate(q):
                if job["id"] == job_id:
                    job["duration_sec"] = minutes * 60
                    # Editing the head clears its countdown and forces a re-apply;
                    # the new countdown starts only once the controller accepts it.
                    if i == 0:
                        job["ends_at"] = None
                        self._retarget()
                    self._bump()
                    break

    def adjust(self, delta_min):
        """+/- on the running head: change the remaining time and re-apply. The
        new countdown restarts only once the controller accepts the new time."""
        with self.lock:
            q = self.state["queue"]
            if q:
                job = q[0]
                # Base the new total on the current remaining time (if running)
                # or the full duration (if not yet started).
                remaining = (job["ends_at"] - time.time()) if job.get("ends_at") else job["duration_sec"]
                new_total = max(60, int(round(remaining + delta_min * 60)))
                job["duration_sec"] = new_total
                job["ends_at"] = None       # clear until re-apply succeeds
                self._retarget()            # force worker to re-apply
                self._bump()

    def stop_current(self):
        """Stop the running head and advance to the next queued item."""
        with self.lock:
            if self.state["queue"]:
                self.state["queue"].pop(0)
                self._bump()

    def stop_all(self):
        with self.lock:
            self.state["queue"] = []
            self._bump()

    # ────────────────────────── worker (single owner of the connection) ─────
    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._worker())

    async def _worker(self):
        """The one task allowed to touch the controller.

        Each tick:
          1. Expire a finished head and advance the queue.
          2. Ensure a session for the configured controller.
          3. If backoff timer hasn't elapsed, just sleep (don't hammer).
          4. Reconcile: compute the single command needed to make the
             controller match the head, apply it, handle success/failure with
             backoff.
          5. When idle and due, do a best-effort rain-sensor read.
        """
        last_poll = 0.0
        while True:
            try:
                self._expire_finished_head()
                await self._ensure_session()
                now = time.time()

                if not self.controller:
                    # Not configured → nothing to drive.
                    with self.lock:
                        self._set_ctrl_state("idle" if not self.state["controller_configured"] else "offline")
                    await self._sleep_until_work(1.0)
                    continue

                if now < self._next_attempt:
                    # In backoff cooldown — wait it out (but wake early on changes).
                    with self.lock:
                        self._set_ctrl_state("retrying")
                    await self._sleep_until_work(self._next_attempt - now)
                    continue

                applied_change = await self._reconcile_once()

                # When idle (no command applied this tick), run the liveness probe
                # periodically so the connection status stays meaningful.
                if not applied_change and time.time() - last_poll > POLL_INTERVAL:
                    await self._poll_health()
                    last_poll = time.time()

                # Idle wait: wake immediately on any state change, else short tick
                # so the countdown-expiry check stays responsive.
                await self._sleep_until_work(1.0)
            except Exception as e:
                with self.lock:
                    self._schedule_retry(e)
                self._set_online(False)
                await self._sleep_until_work(1.0)

    def _expire_finished_head(self):
        """Pop a head whose confirmed countdown has elapsed; advance the queue."""
        with self.lock:
            q = self.state["queue"]
            if q and q[0].get("ends_at") and time.time() >= q[0]["ends_at"] - 0.5:
                q.pop(0)
                self.applied = None        # controller should move on
                self._clear_backoff()
                self._bump()

    async def _sleep_until_work(self, max_secs):
        """Sleep up to max_secs but return early if a client changes state.
        Uses the condition variable so edits/adds wake the worker instantly."""
        deadline = time.time() + max(0.05, max_secs)
        with self.lock:
            v = self.state["version"]
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return
                self.cond.wait(remaining)
                if self.state["version"] != v:
                    return  # something changed — re-evaluate now

    async def _ensure_session(self):
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
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=CMD_TIMEOUT))
            self.controller = async_client.CreateController(self.session, ip, pw)
            self._settings_key = key
            with self.lock:
                self._retarget()   # new controller → re-apply current head

    async def _reconcile_once(self):
        """Apply at most ONE command to converge the controller on the head.
        Returns True if a command was attempted (success or failure)."""
        with self.lock:
            q = self.state["queue"]
            head = dict(q[0]) if q else None
            applied = self.applied

        # Target: stop (no head) or run the head's zone.
        if head is None:
            if applied is None:
                # Nothing to water. Reflect reachability, but don't fight the
                # liveness probe: only assert "ready" when online; when offline,
                # leave the probe's "offline" label intact (don't reset to idle).
                with self.lock:
                    if self.state["controller_online"]:
                        self._set_ctrl_state("ready")
                    elif self.state["controller_state"] not in ("offline", "retrying"):
                        self._set_ctrl_state("idle")
                return False
            # Need to stop.
            try:
                with self.lock: self._set_ctrl_state("connecting")
                await self.controller.stop_irrigation()
                with self.lock:
                    self.applied = None
                    self._clear_backoff()
                    self._set_ctrl_state("idle")
                self._set_online(True)
                return True
            except Exception as e:
                with self.lock: self._schedule_retry(e)
                self._set_online(False)
                return True

        want = (head["id"], head["zone_id"])
        if want == applied:
            # Already running the right zone; nothing to do.
            with self.lock:
                self._set_ctrl_state("watering")
            return False

        # Need to (re)start the head's zone.
        try:
            with self.lock: self._set_ctrl_state("connecting")
            minutes = max(1, math.ceil(head["duration_sec"] / 60))
            if applied is not None:
                await self.controller.stop_irrigation()
                await asyncio.sleep(1)
            await self.controller.irrigate_zone(head["zone_id"], minutes)
            # Confirmed: start the countdown NOW and mark applied.
            with self.lock:
                self._update_job(head["id"], ends_at=time.time() + head["duration_sec"])
                self.applied = want
                self._clear_backoff()
                self._set_ctrl_state("watering")
                self._bump()
            self._set_online(True)
            return True
        except Exception as e:
            with self.lock: self._schedule_retry(e)
            self._set_online(False)
            return True

    async def _poll_health(self):
        """Idle liveness probe — the ONLY way we know the controller is reachable
        when nothing is queued. A successful read marks us online + ready and
        refreshes the rain sensor; a failure feeds the online/offline hysteresis
        (3 strikes → offline). It does NOT touch command backoff — that's reserved
        for real irrigate/stop commands. This is why the status is meaningful at idle."""
        try:
            rain = await self.controller.get_rain_sensor_state()
            with self.lock:
                if self.state["rain_sensor"] != bool(rain):
                    self.state["rain_sensor"] = bool(rain)
                    self._bump()
            self._set_online(True)
            with self.lock:
                if not self.state["queue"]:
                    self._set_ctrl_state("ready")
        except Exception:
            self._set_online(False)
            with self.lock:
                if not self.state["queue"]:
                    self._set_ctrl_state("offline")


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
            "/api/queue/add-many": self._q_add_many,
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

    def _q_add_many(self, b):
        items = [{"zone_id": int(i["zone_id"]), "duration_min": int(i["duration_min"])}
                 for i in b.get("items", [])]
        MANAGER.add_many(items)
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
        order = settings.get("zone_order", [])
        all_ids = list(range(1, 20))
        # Honor saved display order; append any not-yet-ordered ids at the end.
        ordered = [z for z in order if z in all_ids] + [z for z in all_ids if z not in order]
        zones = []
        for zid in ordered:
            zones.append({
                "id": zid,
                "name": names.get(str(zid), f"Zone {zid}"),
                "visible": (not visible) or (zid in visible),
            })
        self.send_json_response({"success": True, "zones": zones,
                                 "visible_zones": visible, "zone_order": order})

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
    # Rain Bird Corporation registered MAC OUI prefixes (first 3 octets).
    RAINBIRD_OUIS = {"50:06:f5"}

    def handle_scan(self):
        try:
            result = self._scan_for_controllers()
            self.send_json_response({"success": True, **result})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e),
                                     "controllers": [], "matched": False})

    def _scan_for_controllers(self):
        """Find and CONFIRM RainBird controllers on the LAN.

        Three signals, strongest first:
          1. Protocol handshake — pyrainbird get_model_and_version() with the
             configured password. If it decrypts a model, the device is a genuine,
             controllable RainBird (we report the model). A "wrong password" error
             still proves it's a controller (it spoke the protocol), just not
             usable with the current password.
          2. MAC OUI — manufacturer is Rain Bird (50:06:F5). Narrows candidates
             but does NOT prove the device is a controller (could be a module).
          3. Port 80 open — weakest; lots of unrelated devices qualify.

        We hand the UI a list of {ip, controllable, model, is_rainbird_mac, reason}
        sorted so confirmed controllers come first.
        """
        subnet = self._get_local_subnet()
        if not subnet:
            return {"devices": [], "controllers": []}
        hosts = [str(h) for h in ipaddress.IPv4Network(subnet, strict=False).hosts()]

        # Prime ARP + find open-80 hosts.
        with ThreadPoolExecutor(max_workers=64) as pool:
            reachable = list(pool.map(self._tcp_probe, hosts))
        open_hosts = [ip for ip, ok in zip(hosts, reachable) if ok]

        arp = self._arp_table()
        mac_hosts = {ip for ip, mac in arp.items() if mac[:8].lower() in self.RAINBIRD_OUIS}

        # Candidates worth a handshake: any Rain Bird-MAC host, plus open-80 hosts.
        candidates = sorted(
            set(open_hosts) | mac_hosts,
            key=lambda ip: tuple(int(o) for o in ip.split("."))
        )

        password = load_settings().get("controller_password", "")
        probes = self._verify_candidates(candidates, password)

        devices = []
        for ip in candidates:
            p = probes.get(ip, {})
            controllable = p.get("controllable", False)
            is_controller = controllable or p.get("is_controller", False)
            devices.append({
                "ip": ip,
                "controllable": controllable,
                "is_controller": is_controller,
                "is_rainbird_mac": ip in mac_hosts,
                "model": p.get("model"),
                "reason": p.get("reason", ""),
            })
        # Sort: controllable first, then known-controller, then RB-MAC, then rest.
        devices.sort(key=lambda d: (not d["controllable"], not d["is_controller"],
                                    not d["is_rainbird_mac"], d["ip"]))
        controllers = [d["ip"] for d in devices if d["controllable"]]
        return {"devices": devices, "controllers": controllers}

    def _verify_candidates(self, ips, password):
        """Run protocol handshakes against candidate IPs in one event loop."""
        if not ips:
            return {}
        loop = asyncio.new_event_loop()
        try:
            async def run_all():
                results = await asyncio.gather(*[_probe_rainbird(ip, password) for ip in ips])
                return {r["ip"]: r for r in results}
            return loop.run_until_complete(run_all())
        finally:
            loop.close()

    def _arp_table(self):
        """Return {ip: mac} from the OS ARP cache. Best-effort, cross-platform."""
        import subprocess, re
        table = {}
        try:
            out = subprocess.run(["arp", "-an"], capture_output=True, text=True, timeout=5).stdout
        except Exception:
            return table
        # Lines look like: "? (192.168.1.109) at 50:6:f5:4d:6a:ad on en0 ..."
        for line in out.splitlines():
            m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)", line)
            if not m:
                continue
            ip, mac = m.group(1), m.group(2)
            # Normalise each octet to two digits (macOS prints "6" not "06").
            mac = ":".join(p.zfill(2) for p in mac.split(":"))
            table[ip] = mac
        return table

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
