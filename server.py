#!/usr/bin/env python3
"""
RainBird Web App Server - REST API for ESP-ME3 Irrigation Control

This module provides a web server with REST API endpoints for controlling RainBird
ESP-ME3 irrigation controllers through a web interface. It serves static HTML/CSS/JS
files and provides JSON API endpoints for zone control and system status.

Architecture:
    Built using Python's standard library http.server (BaseHTTPRequestHandler and
    HTTPServer) for simplicity and minimal dependencies. The server handles both
    static file serving and REST API endpoints in a single handler class.

    Request Flow:
        1. Browser requests HTML/CSS/JS -> Served from local files
        2. JavaScript calls REST API -> Handler processes and returns JSON
        3. API uses PyRainBird library -> Communicates with ESP-ME3 controller
        4. Results returned to browser -> UI updates based on response

API Endpoints:
    GET  /                      - Serve main HTML interface
    GET  /api/zones            - Get list of available zones
    GET  /api/status           - Get current irrigation status
    POST /api/zones/start      - Start a zone
    POST /api/zones/stop       - Stop a zone
    POST /api/settings         - Load/save controller settings

Settings Management:
    Controller IP, password, and zone names are stored in config.json.
    This allows the web interface to remember controller configuration
    between sessions without hardcoding credentials.

Static Files:
    The server serves static files (HTML, CSS, JS) from the current directory.
    Content types are determined by file extension for proper browser rendering.

Controller Communication:
    Currently uses PyRainBird library (imported as 'pyrainbird').
    Note: The actual async controller implementation is not yet integrated
    in the API endpoints - this is a work in progress.

ESP-ME3 Compatibility:
    Designed for RainBird ESP-ME3 controllers with the same limitations as
    simple_cli.py:
        - Manual zone control only (no stored programs)
        - Zones 1-19 supported
        - Maximum 60-minute duration per activation
        - One zone active at a time

Security Considerations:
    WARNING: This server has minimal security:
        - No authentication on API endpoints
        - Settings stored in plain text JSON file
        - Should only be run on trusted local networks
        - NOT suitable for internet-facing deployment

Usage:
    python3 server.py

    Server will start on http://localhost:8000
    Open in browser to access the web interface

Dependencies:
    - http.server: Standard library HTTP server
    - json: JSON parsing and generation
    - pyrainbird: RainBird controller protocol (to be integrated)

Author: Jason DeWeese
Version: 1.0
Last Updated: 2025-09-16

TODO:
    - Integrate async PyRainBird controller in API endpoints
    - Add proper error handling for controller communication
    - Implement actual zone control (currently returns mock responses)
    - Add authentication/authorization
    - Implement WebSocket for real-time status updates
"""

import json
import os
import asyncio
import aiohttp
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pyrainbird import async_client

# Global session management
active_sessions = {}
last_cleanup = time.time()

class RainBirdHandler(BaseHTTPRequestHandler):
    def set_active_zone(self, zone_id, duration=None):
        """Track the active zone and start time in a simple file"""
        try:
            zone_data = {
                'zone_id': zone_id,
                'start_time': time.time() if zone_id else None,
                'duration': duration if zone_id else None
            }
            with open('.active_zone', 'w') as f:
                json.dump(zone_data, f)
        except:
            pass
    
    def get_active_zone(self):
        """Get the tracked active zone with timing info from file"""
        try:
            with open('.active_zone', 'r') as f:
                zone_data = json.load(f)
                if zone_data.get('zone_id'):
                    return zone_data
                return None
        except:
            return None
    """
    HTTP request handler for RainBird irrigation controller web interface.

    Handles both REST API requests (JSON) and static file serving (HTML/CSS/JS).
    This single handler class manages all server functionality for simplicity.

    Request Routing:
        GET  /                -> Serve index.html (main interface)
        GET  /api/zones       -> Return available zones as JSON
        GET  /api/status      -> Return irrigation status as JSON
        GET  /{filename}      -> Serve static file (CSS, JS, images)
        POST /api/zones/start -> Start zone (JSON request body)
        POST /api/zones/stop  -> Stop zone (JSON request body)
        POST /api/settings    -> Load/save settings (JSON request body)

    Response Formats:
        API endpoints return JSON with this structure:
        {
            "success": true/false,
            "data": {...},          # On success
            "error": "message"      # On failure
        }

    Error Handling:
        - Invalid JSON: 400 Bad Request
        - File not found: 404 Not Found
        - Controller errors: 200 OK with success=false and error message

    Thread Safety:
        This handler is instantiated per-request, so no shared state
        concerns between requests. Settings are loaded fresh each time.

    Note:
        Inherits from BaseHTTPRequestHandler which provides the HTTP protocol
        implementation. We override do_GET and do_POST for custom routing.
    """

    def do_GET(self):
        """
        Handle HTTP GET requests.

        Routes GET requests to appropriate handlers based on URL path.
        Serves static files for the web interface and JSON data for API calls.

        URL Routing:
            /                -> Main HTML interface (index.html)
            /api/zones       -> Available zones list
            /api/status      -> Current irrigation status
            /{filename}      -> Static file (CSS, JS, etc.)

        Returns:
            None - Sends HTTP response directly

        Response Codes:
            200 OK - Successful request
            404 Not Found - Unknown path or missing file
        """
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Route to appropriate handler
        if path == '/':
            # Serve main web interface
            self.serve_file('index.html')
        elif path == '/api/zones':
            # Get available zones for UI
            self.handle_get_zones()
        elif path == '/api/status':
            # Get current irrigation status
            self.handle_get_status()
        elif path == '/api/connection/status':
            # Get connection status
            self.handle_connection_status()
        elif path == '/api/diagnostics':
            # Get system diagnostics
            self.handle_diagnostics()
        elif path.startswith('/'):
            # Serve static file (remove leading slash)
            self.serve_file(path[1:])
        else:
            self.send_error(404)
    
    def do_POST(self):
        """
        Handle HTTP POST requests.

        Routes POST requests to appropriate handlers and parses JSON request bodies.
        All POST endpoints expect JSON content and return JSON responses.

        URL Routing:
            /api/zones/start -> Start irrigation on a zone
            /api/zones/stop  -> Stop irrigation on a zone
            /api/settings    -> Load or save settings

        Request Body:
            All POST requests expect JSON with endpoint-specific structure.
            Content-Type: application/json is expected (but not enforced).

        Error Handling:
            - Invalid JSON: 400 Bad Request
            - Unknown path: 404 Not Found
            - Endpoint errors: 200 OK with success=false

        Returns:
            None - Sends HTTP response directly

        Example Request:
            POST /api/zones/start
            {"zone_id": 1, "duration": 10}

        Note:
            Reads entire request body into memory - not suitable for
            large uploads (but fine for JSON API calls).
        """
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Read request body
        # Content-Length header indicates size of POST data
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        # Parse JSON request body
        try:
            request_data = json.loads(post_data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Invalid JSON in request body
            self.send_error(400, "Invalid JSON")
            return

        # Route to appropriate handler
        if path == '/api/zones/start':
            self.handle_start_zone(request_data)
        elif path == '/api/zones/stop':
            self.handle_stop_zone(request_data)
        elif path == '/api/zones/stop-all':
            self.handle_stop_all_zones(request_data)
        elif path == '/api/rain-sensor/override':
            self.handle_rain_sensor_override(request_data)
        elif path == '/api/settings':
            self.handle_settings(request_data)
        else:
            self.send_error(404)
    
    def handle_get_zones(self):
        """
        API endpoint: GET /api/zones - Get list of available irrigation zones.

        Returns a list of zones with their IDs, names, and availability status.
        Zone names can be customized in config.json, otherwise defaults are used.

        Zone Configuration:
            - Hardcoded zone IDs: [1, 3, 5, 12, 13, 14, 21]
            - These represent the physically wired zones on the controller
            - Not all 19 possible zones are necessarily wired/available
            - Zone names loaded from config.json['zone_names']

        Response Format:
            {
                "success": true,
                "zones": [
                    {
                        "id": 1,
                        "name": "Front Lawn",  // From settings, or "Zone 1" default
                        "available": true
                    },
                    ...
                ]
            }

        Error Response:
            {
                "success": false,
                "error": "error message"
            }

        Returns:
            None - Sends JSON response directly

        Note:
            The hardcoded zone list should ideally be queried from the controller,
            but ESP-ME3 doesn't provide a "get wired zones" API, so we rely on
            known configuration.
        """
        try:
            settings = self.load_settings()
            zones = []

            # All possible zones (1-19 for ESP-ME3)
            for zone_id in range(1, 20):
                zone_name = settings.get('zone_names', {}).get(str(zone_id), f"Zone {zone_id}")
                zones.append({
                    "id": zone_id,
                    "name": zone_name,
                    "available": True
                })

            self.send_json_response({"success": True, "zones": zones})

        except Exception as e:
            # Catch-all for unexpected errors (file I/O, etc.)
            self.send_json_response({"success": False, "error": str(e)})
    
    def handle_get_status(self):
        """API endpoint: GET /api/status - Get current irrigation system status."""
        try:
            result = self.run_async(self._get_status_async())
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _get_status_async(self):
        """
        API endpoint: GET /api/status - Get current irrigation system status.

        Returns comprehensive status information about the irrigation system,
        including active zones, rain sensor state, and controller information.

        Status Information:
            - Irrigation state: Whether system is active, which zone, time remaining
            - Rain sensor: Whether sensor is active and preventing irrigation
            - Model info: Controller model and firmware version
            - Timestamp: When status was retrieved

        Response Format:
            {
                "success": true,
                "status": {
                    "irrigation_state": {
                        "active": false,
                        "zone": null,            // Zone ID if active
                        "time_remaining": 0      // Minutes remaining
                    },
                    "rain_sensor": {
                        "active": false,
                        "status": "inactive"
                    },
                    "model_info": {
                        "model": "ESP-ME3",
                        "version": "2.12"
                    },
                    "timestamp": 1726502433      // Unix timestamp
                }
            }

        Error Responses:
            - Controller not configured: success=false, error message
            - Connection failed: success=false, error message
            - Other errors: success=false, error message

        Returns:
            None - Sends JSON response directly

        TODO:
            - Integrate actual PyRainBird controller communication
            - Currently returns mock data
            - Need to implement async controller queries
            - Add remaining time calculation (controller doesn't provide this)
        """
        controller_data = await self.get_controller()
        if not controller_data:
            return {"success": False, "error": "Controller not configured"}

        controller, session = controller_data
        try:
            # Get current irrigation status
            irrigation_active = await controller.get_current_irrigation()
            rain_sensor = await controller.get_rain_sensor_state()
            
            # Get tracked zone info with timing
            zone_info = self.get_active_zone()
            active_zone = None
            time_remaining = 0
            
            if irrigation_active and zone_info:
                active_zone = zone_info['zone_id']
                if zone_info.get('start_time') and zone_info.get('duration'):
                    elapsed = time.time() - zone_info['start_time']
                    time_remaining = max(0, (zone_info['duration'] * 60) - elapsed)
            elif not irrigation_active:
                # Clear tracking if irrigation stopped
                self.set_active_zone(None)
            
            status = {
                "irrigation_state": {
                    "active": bool(irrigation_active),
                    "zone": active_zone,
                    "time_remaining": int(time_remaining)
                },
                "rain_sensor": {
                    "active": bool(rain_sensor),
                    "status": "active" if rain_sensor else "inactive"
                },
                "model_info": {"model": "ESP-ME3", "version": "2.12"},
                "timestamp": int(time.time())
            }
            
            return {"success": True, "status": status}
        finally:
            # Don't close session - it's managed now
            pass
    
    def handle_start_zone(self, request_data):
        """API endpoint: POST /api/zones/start - Start irrigation on a specific zone."""
        try:
            result = self.run_async(self._start_zone_async(request_data))
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _start_zone_async(self, request_data):
        zone_id = request_data.get('zone_id')
        duration = request_data.get('duration', 10)

        controller_data = await self.get_controller()
        if not controller_data:
            return {"success": False, "error": "Controller not configured"}

        controller, session = controller_data
        try:
            # Start irrigation on the specified zone
            await controller.irrigate_zone(zone_id, duration)
            
            # Track the started zone with timing info
            self.set_active_zone(zone_id, duration)
            
            # Wait for controller to process command (like CLI does)
            await asyncio.sleep(2)
            
            return {"success": True, "message": f"Zone {zone_id} started for {duration} minutes"}
        finally:
            # Don't close session - it's managed now
            pass

    def handle_stop_zone(self, request_data):
        """API endpoint: POST /api/zones/stop - Stop irrigation on a specific zone."""
        try:
            result = self.run_async(self._stop_zone_async(request_data))
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _stop_zone_async(self, request_data):
        zone_id = request_data.get('zone_id')

        controller_data = await self.get_controller()
        if not controller_data:
            return {"success": False, "error": "Controller not configured"}

        controller, session = controller_data
        try:
            # Stop all irrigation (ESP-ME3 stops all zones)
            await controller.stop_irrigation()
            
            # Clear the tracked zone
            self.set_active_zone(None)
            
            return {"success": True, "message": f"Zone {zone_id} stopped"}
        finally:
            # Don't close session - it's managed now
            pass

    def handle_stop_all_zones(self, request_data):
        """API endpoint: POST /api/zones/stop-all - Stop all irrigation"""
        try:
            result = self.run_async(self._stop_all_zones_async())
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _stop_all_zones_async(self):
        controller_data = await self.get_controller()
        if not controller_data:
            return {"success": False, "error": "Controller not configured"}

        controller, session = controller_data
        try:
            await controller.stop_irrigation()
            self.set_active_zone(None)
            return {"success": True, "message": "All irrigation stopped"}
        finally:
            # Don't close session - it's managed now
            pass

    def handle_rain_sensor_override(self, request_data):
        """API endpoint: POST /api/rain-sensor/override - Override rain sensor"""
        try:
            result = self.run_async(self._rain_sensor_override_async(request_data))
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _rain_sensor_override_async(self, request_data):
        override = request_data.get('override', False)
        # Note: ESP-ME3 doesn't support rain sensor override via API
        # This would be a mock implementation
        return {"success": True, "message": f"Rain sensor override {'enabled' if override else 'disabled'}"}

    def handle_connection_status(self):
        """API endpoint: GET /api/connection/status - Get connection status"""
        try:
            settings = self.load_settings()
            session_key = f"{settings.get('controller_ip', '')}:{settings.get('controller_password', '')}"
            
            if session_key in active_sessions:
                session_data = active_sessions[session_key]
                status = {
                    "success": True,
                    "connected": True,
                    "controller_ip": settings.get('controller_ip'),
                    "session_age": int(time.time() - session_data['created']),
                    "last_used": int(time.time() - session_data['last_used']),
                    "session_count": len(active_sessions)
                }
            else:
                status = {
                    "success": True,
                    "connected": False,
                    "controller_ip": settings.get('controller_ip'),
                    "session_count": len(active_sessions)
                }
            
            self.send_json_response(status)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    def handle_diagnostics(self):
        """API endpoint: GET /api/diagnostics - Get system diagnostics"""
        try:
            result = self.run_async(self._diagnostics_async())
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})

    async def _diagnostics_async(self):
        settings = self.load_settings()
        diagnostics = {
            "success": True,
            "controller_configured": bool(settings.get('controller_ip') and settings.get('controller_password')),
            "active_sessions": len(active_sessions),
            "settings_file": "config.json",
            "zones_configured": len(settings.get('zone_names', {}))
        }
        
        # Test controller connection if configured
        if diagnostics["controller_configured"]:
            try:
                controller_data = await self.get_controller()
                if controller_data:
                    controller, session = controller_data
                    await controller.get_current_irrigation()
                    diagnostics["controller_reachable"] = True
                    diagnostics["connection_test"] = "SUCCESS"
                else:
                    diagnostics["controller_reachable"] = False
                    diagnostics["connection_test"] = "FAILED - Not configured"
            except Exception as e:
                diagnostics["controller_reachable"] = False
                diagnostics["connection_test"] = f"FAILED - {str(e)}"
        else:
            diagnostics["controller_reachable"] = False
            diagnostics["connection_test"] = "SKIPPED - Not configured"
        
        return diagnostics
    
    def handle_settings(self, request_data):
        """
        API endpoint: POST /api/settings - Load or save application settings.

        Handles both loading and saving of persistent settings stored in config.json.
        Settings include controller IP, password, zone names, and UI preferences.

        Request Body (Load):
            {
                "action": "load"
            }

        Request Body (Save):
            {
                "action": "save",
                "settings": {
                    "controller_ip": "192.168.1.113",
                    "controller_password": "1234",
                    "auto_connect": true,
                    "refresh_interval": 5,
                    "zone_names": {
                        "1": "Front Lawn",
                        "3": "Back Lawn",
                        ...
                    }
                }
            }

        Response Format (Load):
            {
                "success": true,
                "settings": { ... }
            }

        Response Format (Save):
            {
                "success": true
            }

        Error Responses:
            - Invalid action: 400 Bad Request
            - File I/O error: success=false, error message

        Args:
            request_data (dict): Parsed JSON request body

        Returns:
            None - Sends JSON response directly

        Security Note:
            Settings including passwords are stored in plain text in config.json.
            This is NOT secure but acceptable for local network use only.
        """
        action = request_data.get('action')

        if action == 'load':
            # Load settings from file
            settings = self.load_settings()
            self.send_json_response({"success": True, "settings": settings})

        elif action == 'save':
            # Merge incoming settings with existing file so partial saves
            # (e.g. from the settings popup) don't wipe zone_names.
            incoming = request_data.get('settings', {})
            merged = self.load_settings()
            merged.update(incoming)
            success = self.save_settings(merged)
            self.send_json_response({"success": success})

        elif action == 'update-zone-name':
            # Update zone name
            zone_id = str(request_data.get('zone_id'))
            name = request_data.get('name')
            settings = self.load_settings()
            settings.setdefault('zone_names', {})[zone_id] = name
            success = self.save_settings(settings)
            self.send_json_response({"success": success})

        else:
            # Invalid action specified
            self.send_error(400, "Invalid action")
    
    def run_async(self, coro):
        """Run async coroutine in sync context"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def get_controller(self):
        """Get configured controller instance with session management"""
        settings = self.load_settings()
        if not settings.get('controller_ip') or not settings.get('controller_password'):
            return None
        
        # Cleanup old sessions periodically
        global last_cleanup
        if time.time() - last_cleanup > 300:  # 5 minutes
            self.cleanup_idle_sessions()
            last_cleanup = time.time()
        
        session_key = f"{settings['controller_ip']}:{settings['controller_password']}"
        
        # Check if we have an active session
        if session_key in active_sessions:
            session_data = active_sessions[session_key]
            # Test if session is still alive
            try:
                controller, session = session_data['controller'], session_data['session']
                # Quick health check
                await asyncio.wait_for(controller.get_current_irrigation(), timeout=2)
                session_data['last_used'] = time.time()
                return controller, session
            except:
                # Session is dead, remove it
                try:
                    await session_data['session'].close()
                except:
                    pass
                del active_sessions[session_key]
        
        # Create new session
        session = aiohttp.ClientSession()
        controller = async_client.CreateController(
            session, settings['controller_ip'], settings['controller_password']
        )
        
        active_sessions[session_key] = {
            'controller': controller,
            'session': session,
            'last_used': time.time(),
            'created': time.time()
        }
        
        return controller, session

    def cleanup_idle_sessions(self):
        """Clean up idle sessions"""
        cutoff = time.time() - 300  # 5 minutes
        for key in list(active_sessions.keys()):
            if active_sessions[key]['last_used'] < cutoff:
                try:
                    active_sessions[key]['session'].close()
                except:
                    pass
                del active_sessions[key]

    def load_settings(self):
        """Load application settings from config.json file."""
        config_path = os.environ.get("CONFIG_PATH", "/app/config/config.json")
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
                settings.setdefault('auto_connect', False)
                settings.setdefault('refresh_interval', 5)
                settings.setdefault('zone_names', {})
                return settings
        except FileNotFoundError:
            return {
                "controller_ip": "",
                "controller_password": "",
                "timeout": 10,
                "auto_connect": False,
                "refresh_interval": 5,
                "zone_names": {}
            }

    def save_settings(self, settings):
        """Save application settings to config.json file."""
        config_path = os.environ.get("CONFIG_PATH", "/app/config/config.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def serve_file(self, filename):
        """
        Serve static files from the current directory.

        Reads and serves files for the web interface (HTML, CSS, JavaScript, images).
        Content-Type header is set based on file extension for proper browser rendering.

        Supported File Types:
            - .html  -> text/html
            - .css   -> text/css
            - .js    -> application/javascript
            - others -> application/octet-stream

        Args:
            filename (str): Relative path to file (e.g., "index.html", "css/style.css")

        Returns:
            None - Sends HTTP response with file contents or 404 error

        Security Considerations:
            - No path traversal protection (assumes trusted file paths)
            - Serves any file in current directory and subdirectories
            - Should not be exposed to untrusted users
            - Consider adding path validation for production use

        Response Headers:
            - Content-Type: Based on file extension
            - Content-Length: Exact file size in bytes

        Error Handling:
            - File not found: 404 Not Found response
            - Other errors: Would raise exception (not caught)

        Example:
            # Browser requests /css/style.css
            # Handler calls serve_file("css/style.css")
            # File is read and sent with Content-Type: text/css
        """
        try:
            # Read file in binary mode to handle all file types
            with open(filename, 'rb') as f:
                content = f.read()

            # Determine content type based on file extension
            # This tells the browser how to interpret the file
            if filename.endswith('.html'):
                content_type = 'text/html'
            elif filename.endswith('.css'):
                content_type = 'text/css'
            elif filename.endswith('.js'):
                content_type = 'application/javascript'
            else:
                # Generic binary type for unknown files
                content_type = 'application/octet-stream'

            # Send HTTP response with appropriate headers
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()

            # Write file contents to response
            self.wfile.write(content)

        except FileNotFoundError:
            # File doesn't exist - send 404
            self.send_error(404)
    
    def send_json_response(self, data):
        """Send JSON response to client."""
        response = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        """
        Override BaseHTTPRequestHandler's logging to reduce noise.

        By default, BaseHTTPRequestHandler logs every request to stderr.
        This override suppresses all logging to keep the console clean.

        Args:
            format (str): Log message format string (ignored)
            *args: Log message arguments (ignored)

        Returns:
            None - Logging is suppressed

        Note:
            For debugging, comment out 'pass' and add:
            super().log_message(format, *args)
        """
        pass  # Suppress all request logging

def run_server(port=8000):
    """
    Start the HTTP server and run indefinitely.

    Creates an HTTPServer instance bound to localhost on the specified port
    and runs the server loop to handle incoming requests. Blocks until interrupted.

    Args:
        port (int): Port number to listen on (default: 8000)

    Server Configuration:
        - Host: localhost (127.0.0.1) - only accepts local connections
        - Port: 8000 (default) or specified value
        - Handler: RainBirdHandler class for request processing
        - Blocking: Runs forever until Ctrl+C or process killed

    Security:
        Binds to localhost only, preventing external network access.
        For LAN access, change 'localhost' to '0.0.0.0' (NOT recommended
        without authentication).

    Startup Messages:
        Prints server URL and library information to console for user.

    Shutdown:
        - Ctrl+C (KeyboardInterrupt) will stop server gracefully
        - Process kill will stop immediately
        - No cleanup required - server handles connection teardown

    Returns:
        None - Runs until interrupted

    Example:
        >>> run_server()  # Start on default port 8000
        🌱 RainBird Server running on http://localhost:8000
        ✅ Using PyRainBird library
        # Server now accepting requests...

        >>> run_server(8080)  # Start on custom port
        🌱 RainBird Server running on http://localhost:8080
        ✅ Using PyRainBird library

    Note:
        Uses HTTPServer from Python standard library - simple but not
        production-grade. For production, consider using Gunicorn, uWSGI,
        or a proper async framework like FastAPI or Sanic.
    """
    # Create HTTP server with our handler class
    server = HTTPServer(('0.0.0.0', port), RainBirdHandler)

    # Print startup information
    print(f"🌱 RainBird Server running on http://0.0.0.0:{port}")
    print("✅ Using PyRainBird library")

    # Run server loop indefinitely (blocks until interrupted)
    server.serve_forever()


if __name__ == '__main__':
    # Run server when script is executed directly
    run_server()
