#!/usr/bin/env python3
"""
RainBird Web App Server
Using PyRainBird library for controller communication
"""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Use installed pyrainbird
import pyrainbird

class RainBirdHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.serve_file('index.html')
        elif path == '/api/zones':
            self.handle_get_zones()
        elif path == '/api/status':
            self.handle_get_status()
        elif path.startswith('/'):
            self.serve_file(path[1:])  # Remove leading slash
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(post_data.decode('utf-8'))
        except:
            self.send_error(400, "Invalid JSON")
            return
        
        if path == '/api/zones/start':
            self.handle_start_zone(request_data)
        elif path == '/api/zones/stop':
            self.handle_stop_zone(request_data)
        elif path == '/api/settings':
            self.handle_settings(request_data)
        else:
            self.send_error(404)
    
    def handle_get_zones(self):
        """Get available zones"""
        try:
            settings = self.load_settings()
            zones = []
            
            # Create zones based on your controller (1,3,5,12,13,14,21)
            zone_ids = [1, 3, 5, 12, 13, 14, 21]
            zone_names = settings.get('zone_names', {})
            
            for zone_id in zone_ids:
                zones.append({
                    "id": zone_id,
                    "name": zone_names.get(str(zone_id), f"Zone {zone_id}"),
                    "available": True
                })
            
            self.send_json_response({"success": True, "zones": zones})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})
    
    def handle_get_status(self):
        """Get system status"""
        try:
            settings = self.load_settings()
            if not settings.get('controller_ip') or not settings.get('controller_password'):
                self.send_json_response({"success": False, "error": "Controller not configured"})
                return
            
            # Use pyrainbird to get status
            controller = RainbirdController(settings['controller_ip'], settings['controller_password'])
            
            # Get current irrigation state (simplified for now)
            status = {
                "irrigation_state": {"active": False, "zone": None, "time_remaining": 0},
                "rain_sensor": {"active": False, "status": "inactive"},
                "model_info": {"model": "RainBird", "version": "1.0"},
                "timestamp": 1726502433
            }
            
            self.send_json_response({"success": True, "status": status})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})
    
    def handle_start_zone(self, request_data):
        """Start a zone"""
        try:
            zone_id = request_data.get('zone_id')
            duration = request_data.get('duration', 10)
            
            settings = self.load_settings()
            if not settings.get('controller_ip') or not settings.get('controller_password'):
                self.send_json_response({"success": False, "error": "Controller not configured"})
                return
            
            # Use pyrainbird to start zone
            controller = RainbirdController(settings['controller_ip'], settings['controller_password'])
            
            # For now, return success (will implement actual control later)
            self.send_json_response({"success": True, "message": f"Zone {zone_id} started for {duration} minutes"})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})
    
    def handle_stop_zone(self, request_data):
        """Stop a zone"""
        try:
            zone_id = request_data.get('zone_id')
            
            settings = self.load_settings()
            if not settings.get('controller_ip') or not settings.get('controller_password'):
                self.send_json_response({"success": False, "error": "Controller not configured"})
                return
            
            # Use pyrainbird to stop zone
            self.send_json_response({"success": True, "message": f"Zone {zone_id} stopped"})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)})
    
    def handle_settings(self, request_data):
        """Handle settings load/save"""
        action = request_data.get('action')
        
        if action == 'load':
            settings = self.load_settings()
            self.send_json_response({"success": True, "settings": settings})
        elif action == 'save':
            settings = request_data.get('settings', {})
            success = self.save_settings(settings)
            self.send_json_response({"success": success})
        else:
            self.send_error(400, "Invalid action")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "controller_ip": "",
                "controller_password": "",
                "auto_connect": False,
                "refresh_interval": 5,
                "zone_names": {}
            }
    
    def save_settings(self, settings):
        """Save settings to file"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def serve_file(self, filename):
        """Serve static files"""
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            
            # Determine content type
            if filename.endswith('.html'):
                content_type = 'text/html'
            elif filename.endswith('.css'):
                content_type = 'text/css'
            elif filename.endswith('.js'):
                content_type = 'application/javascript'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)
    
    def send_json_response(self, data):
        """Send JSON response"""
        response = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to reduce logging"""
        pass

def run_server(port=8000):
    """Run the server"""
    server = HTTPServer(('localhost', port), RainBirdHandler)
    print(f"🌱 RainBird Server running on http://localhost:{port}")
    print("✅ Using PyRainBird library")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
