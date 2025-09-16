#!/usr/bin/env python3
"""
RainBird Web Server
Serves the web application and handles API requests
"""

import http.server
import socketserver
import json
import os
from lib.rainbird_controller import RainBirdController
from lib.settings_manager import SettingsManager

def load_config():
    try:
        with open('server-config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"port": 8000, "host": "localhost", "timeout": 10, "debug": True}

config = load_config()
PORT = config.get('port', 8000)

class RainBirdHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.settings_manager = SettingsManager()
        super().__init__(*args, **kwargs)
        
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/proxy':
            self.handle_proxy_request()
        elif self.path == '/api/settings':
            self.handle_settings_request()
        elif self.path == '/log':
            self.handle_log_request()
        else:
            self.send_error(404)

    def handle_proxy_request(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            url = request_data.get('url', '')
            data = request_data.get('data', {})
            encrypt = request_data.get('encrypt', False)
            password = request_data.get('password', '')
            
            if not encrypt or not password:
                self.send_error(400, "Encryption required")
                return
            
            # Extract IP from URL
            controller_ip = url.replace('http://', '').replace('/stick', '')
            
            print(f"RainBird request to {controller_ip}")
            
            # Use the modular controller
            controller = RainBirdController(controller_ip, password)
            result = controller.connection.make_request(controller_ip, password, data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            print(f"Proxy error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"success": False, "error": str(e)})
            self.wfile.write(error_response.encode('utf-8'))

    def handle_settings_request(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            action = request_data.get('action')
            
            if action == 'load':
                settings = self.settings_manager.load_settings()
                print(f"DEBUG: Loaded settings: {settings}")
                # Only mask password for settings modal, not for auto-connect
                result = {"success": True, "settings": settings}
                
            elif action == 'save':
                settings_data = request_data.get('settings', {})
                # Don't save masked passwords
                if settings_data.get('controller_password') == '****':
                    current_settings = self.settings_manager.load_settings()
                    settings_data['controller_password'] = current_settings.get('controller_password', '')
                
                success = self.settings_manager.save_settings(settings_data)
                result = {"success": success}
                
            else:
                result = {"success": False, "error": "Unknown action"}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            print(f"Settings error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"success": False, "error": str(e)})
            self.wfile.write(error_response.encode('utf-8'))

    def handle_log_request(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            log_data = json.loads(post_data.decode('utf-8'))
            
            print(f"[Client Log] {log_data.get('message', '')}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            
        except Exception as e:
            print(f"Log error: {e}")
            self.send_response(500)
            self.end_headers()

if __name__ == "__main__":
    print(f"Starting RainBird server on http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), RainBirdHandler) as httpd:
        httpd.serve_forever()
