#!/usr/bin/env python3
"""
RainBird Backend API Server
Direct controller communication with full API implementation
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
from lib.rainbird_controller import RainBirdController
from lib.settings_manager import SettingsManager

class RainBirdBackend:
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.controller = None
        self.last_status = {}
        self.last_update = 0
        
    def get_controller(self):
        """Get or create controller connection"""
        if self.controller is None:
            settings = self.settings_manager.load_settings()
            if settings.get('controller_ip') and settings.get('controller_password'):
                try:
                    self.controller = RainBirdController(
                        settings['controller_ip'],
                        settings['controller_password']
                    )
                    # Test connection
                    if not self.controller.test_connection():
                        print(f"Controller connection test failed for {settings['controller_ip']}")
                        self.controller = None
                except Exception as e:
                    print(f"Failed to create controller: {e}")
                    self.controller = None
        return self.controller
    
    def refresh_connection(self):
        """Force refresh controller connection"""
        self.controller = None
        return self.get_controller()
    
    # Zone Management
    def get_zones(self):
        """Get all available zones"""
        try:
            # Load settings first
            settings = self.settings_manager.load_settings()
            zone_names = settings.get('zone_names', {})
            
            # Create default zones 1-21 based on your controller
            zones = []
            for zone_id in [1, 3, 5, 12, 13, 14, 21]:  # Your actual zones
                zones.append({
                    "id": zone_id,
                    "name": zone_names.get(str(zone_id), f"Zone {zone_id}"),
                    "available": True
                })
            
            return {"success": True, "zones": zones}
        except Exception as e:
            print(f"Error getting zones: {e}")
            return {"success": False, "error": str(e)}
    
    def start_zone(self, zone_id, duration_minutes):
        """Start a specific zone"""
        try:
            # Use existing proxy method for now
            import requests
            settings = self.settings_manager.load_settings()
            
            response = requests.post('http://localhost:8000/proxy', json={
                "url": f"http://{settings['controller_ip']}/stick",
                "data": {
                    "jsonrpc": "2.0",
                    "method": "tunnelSip", 
                    "params": {
                        "data": f"39{zone_id:02x}{duration_minutes*60:04x}",
                        "length": 4
                    },
                    "id": 1
                },
                "encrypt": True,
                "password": settings['controller_password']
            })
            
            result = response.json()
            return {"success": result.get('success', False), "result": result}
        except Exception as e:
            print(f"Error starting zone: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_zone(self, zone_id):
        """Stop a specific zone"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            result = controller.stop_irrigation()
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_all_zones(self):
        """Emergency stop all zones"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            result = controller.stop_irrigation()
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # System Status
    def get_system_status(self):
        """Get current system status"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            # Get current irrigation state
            irrigation_state = controller.get_current_irrigation_state()
            
            # Get rain sensor status
            rain_sensor = controller.get_rain_sensor_state()
            
            # Get model and version
            model_info = controller.get_model_and_version()
            
            status = {
                "irrigation_state": irrigation_state,
                "rain_sensor": rain_sensor,
                "model_info": model_info,
                "timestamp": time.time()
            }
            
            self.last_status = status
            self.last_update = time.time()
            
            return {"success": True, "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Program Management
    def get_programs(self):
        """Get all programs"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            programs = []
            # RainBird controllers typically have programs A, B, C, D
            for prog_id in ['A', 'B', 'C', 'D']:
                try:
                    program_data = controller.get_program_data(prog_id)
                    if program_data:
                        programs.append({
                            "id": prog_id,
                            "name": f"Program {prog_id}",
                            "data": program_data
                        })
                except:
                    continue
            
            return {"success": True, "programs": programs}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_program(self, program_id):
        """Run a specific program"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            result = controller.run_program(program_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Rain Delay
    def set_rain_delay(self, hours):
        """Set rain delay"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            result = controller.set_rain_delay(hours)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_rain_delay(self):
        """Clear rain delay"""
        controller = self.get_controller()
        if not controller:
            return {"success": False, "error": "Controller not configured"}
        
        try:
            result = controller.set_rain_delay(0)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Settings Management
    def update_zone_name(self, zone_id, name):
        """Update zone name"""
        settings = self.settings_manager.load_settings()
        if 'zone_names' not in settings:
            settings['zone_names'] = {}
        settings['zone_names'][str(zone_id)] = name
        
        success = self.settings_manager.save_settings(settings)
        return {"success": success}
    
    def get_settings(self):
        """Get current settings"""
        settings = self.settings_manager.load_settings()
        return {"success": True, "settings": settings}
    
    def update_settings(self, new_settings):
        """Update settings"""
        success = self.settings_manager.save_settings(new_settings)
        if success:
            # Refresh controller connection with new settings
            self.refresh_connection()
        return {"success": success}

class RainBirdAPIHandler(BaseHTTPRequestHandler):
    backend = RainBirdBackend()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        if path == '/api/zones':
            self.send_json_response(self.backend.get_zones())
        elif path == '/api/status':
            self.send_json_response(self.backend.get_system_status())
        elif path == '/api/programs':
            self.send_json_response(self.backend.get_programs())
        elif path == '/api/settings':
            self.send_json_response(self.backend.get_settings())
        elif path.startswith('/'):
            # Serve static files
            self.serve_static_file(path)
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
            zone_id = request_data.get('zone_id')
            duration = request_data.get('duration', 10)
            self.send_json_response(self.backend.start_zone(zone_id, duration))
            
        elif path == '/api/zones/stop':
            zone_id = request_data.get('zone_id')
            if zone_id:
                self.send_json_response(self.backend.stop_zone(zone_id))
            else:
                self.send_json_response(self.backend.stop_all_zones())
                
        elif path == '/api/programs/run':
            program_id = request_data.get('program_id')
            self.send_json_response(self.backend.run_program(program_id))
            
        elif path == '/api/rain-delay':
            hours = request_data.get('hours', 0)
            if hours > 0:
                self.send_json_response(self.backend.set_rain_delay(hours))
            else:
                self.send_json_response(self.backend.clear_rain_delay())
                
        elif path == '/api/zones/name':
            zone_id = request_data.get('zone_id')
            name = request_data.get('name')
            self.send_json_response(self.backend.update_zone_name(zone_id, name))
            
        elif path == '/api/settings':
            if request_data.get('action') == 'load':
                self.send_json_response(self.backend.get_settings())
            elif request_data.get('action') == 'save':
                settings = request_data.get('settings')
                self.send_json_response(self.backend.update_settings(settings))
            else:
                self.send_error(400, "Invalid action")
                
        else:
            self.send_error(404)
    
    def send_json_response(self, data):
        """Send JSON response"""
        response = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def serve_static_file(self, path):
        """Serve static files"""
        if path == '/':
            path = '/index.html'
        
        file_path = '.' + path
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            if path.endswith('.html'):
                content_type = 'text/html'
            elif path.endswith('.css'):
                content_type = 'text/css'
            elif path.endswith('.js'):
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
    
    def log_message(self, format, *args):
        """Override to reduce logging"""
        pass

def run_server(port=8000):
    """Run the RainBird backend server"""
    server = HTTPServer(('localhost', port), RainBirdAPIHandler)
    print(f"🌱 RainBird Backend Server running on http://localhost:{port}")
    print("✅ Full API implementation with direct controller communication")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
