#!/usr/bin/env python3
"""
Enhanced RainBird Controller - Full API Implementation
Direct controller communication with complete feature set
"""

import json
import time
from .rainbird_connection import RainBirdConnection
from .rainbird_protocol import RainBirdProtocol
from .data_formatter import RainBirdFormatter

class RainBirdController:
    """Enhanced RainBird controller with full API implementation"""
    
    def __init__(self, ip_address, password):
        self.connection = RainBirdConnection()
        self.protocol = RainBirdProtocol()
        self.formatter = RainBirdFormatter()
        self.ip_address = ip_address
        self.password = password
    
    # Core Communication
    def send_command(self, command_data, length):
        """Send command to controller"""
        try:
            response = self.connection.send_encrypted_request(
                self.ip_address, self.password, command_data, length
            )
            return response
        except Exception as e:
            print(f"Command error: {e}")
            return None
    
    # System Information
    def get_model_and_version(self):
        """Get controller model and version"""
        response = self.send_command("02", 1)
        if response:
            return self.formatter.format_model_version(response)
        return None
    
    def get_available_stations(self):
        """Get list of available zones/stations"""
        response = self.send_command("10", 1)
        if response and 'data' in response:
            return self.formatter.parse_available_stations(response['data'])
        return []
    
    def get_serial_number(self):
        """Get controller serial number"""
        response = self.send_command("03", 1)
        if response:
            return self.formatter.format_serial_number(response)
        return None
    
    # Irrigation Control
    def start_irrigation(self, zone_id, duration_minutes):
        """Start irrigation for specific zone"""
        duration_seconds = duration_minutes * 60
        zone_hex = f"{zone_id:02x}"
        duration_hex = f"{duration_seconds:04x}"
        command = f"39{zone_hex}{duration_hex}"
        
        response = self.send_command(command, 4)
        return response
    
    def stop_irrigation(self):
        """Stop all irrigation"""
        response = self.send_command("40", 1)
        return response
    
    def get_current_irrigation_state(self):
        """Get current irrigation status"""
        response = self.send_command("48", 1)
        if response and 'data' in response:
            return self.formatter.parse_irrigation_state(response['data'])
        return None
    
    # Rain Sensor
    def get_rain_sensor_state(self):
        """Get rain sensor status"""
        response = self.send_command("3E", 1)
        if response and 'data' in response:
            return self.formatter.parse_rain_sensor(response['data'])
        return None
    
    def set_rain_delay(self, hours):
        """Set rain delay in hours"""
        hours_hex = f"{hours:02x}"
        command = f"36{hours_hex}"
        response = self.send_command(command, 2)
        return response
    
    def get_rain_delay_state(self):
        """Get current rain delay status"""
        response = self.send_command("37", 1)
        if response and 'data' in response:
            return self.formatter.parse_rain_delay(response['data'])
        return None
    
    # Program Management
    def run_program(self, program_id):
        """Run a specific program (A, B, C, D)"""
        program_map = {'A': '01', 'B': '02', 'C': '03', 'D': '04'}
        if program_id not in program_map:
            raise ValueError("Invalid program ID. Use A, B, C, or D")
        
        command = f"38{program_map[program_id]}"
        response = self.send_command(command, 2)
        return response
    
    def get_program_data(self, program_id):
        """Get program configuration data"""
        program_map = {'A': '20', 'B': '21', 'C': '22', 'D': '23'}
        if program_id not in program_map:
            return None
        
        response = self.send_command(program_map[program_id], 1)
        if response and 'data' in response:
            return self.formatter.parse_program_data(response['data'])
        return None
    
    # Water Budget/Seasonal Adjustment
    def get_water_budget(self):
        """Get current water budget percentage"""
        response = self.send_command("30", 1)
        if response and 'data' in response:
            return self.formatter.parse_water_budget(response['data'])
        return None
    
    def set_water_budget(self, percentage):
        """Set water budget percentage (10-200%)"""
        if not 10 <= percentage <= 200:
            raise ValueError("Water budget must be between 10% and 200%")
        
        percentage_hex = f"{percentage:02x}"
        command = f"31{percentage_hex}"
        response = self.send_command(command, 2)
        return response
    
    # Date and Time
    def get_current_time(self):
        """Get controller current time"""
        response = self.send_command("60", 1)
        if response and 'data' in response:
            return self.formatter.parse_current_time(response['data'])
        return None
    
    # Utility Methods
    def test_connection(self):
        """Test connection to controller"""
        try:
            response = self.get_model_and_version()
            return response is not None
        except:
            return False
    
    def get_full_status(self):
        """Get comprehensive system status"""
        return {
            'model_info': self.get_model_and_version(),
            'available_stations': self.get_available_stations(),
            'irrigation_state': self.get_current_irrigation_state(),
            'rain_sensor': self.get_rain_sensor_state(),
            'rain_delay': self.get_rain_delay_state(),
            'water_budget': self.get_water_budget(),
            'current_time': self.get_current_time(),
            'timestamp': time.time()
        }
    
    def _execute_command(self, command_name, *params):
        """Execute a command and return formatted response"""
        # Build request
        request_data = self.protocol.build_request(command_name, *params)
        
        # Send request
        result = self.connection.make_request(self.ip_address, self.password, request_data)
        
        if not result["success"]:
            raise Exception(result["error"])
        
        # Process response
        processed = self.protocol.process_response(result["data"], command_name)
        
        # Format response
        formatted = self.formatter.format_response(processed, command_name)
        
        return formatted
    
    def get_model_version(self):
        """Get controller model and version"""
        return self._execute_command("ModelAndVersionRequest")
    
    def get_zones(self):
        """Get available zones"""
        return self._execute_command("AvailableStationsRequest", "00")
    
    def get_irrigation_status(self):
        """Get current irrigation status"""
        return self._execute_command("CurrentIrrigationStateRequest")
    
    def get_rain_sensor_status(self):
        """Get rain sensor status"""
        return self._execute_command("CurrentRainSensorStateRequest")
    
    def get_current_time(self):
        """Get controller current time"""
        return self._execute_command("CurrentTimeRequest")
    
    def get_program_info(self):
        """Get program information"""
        return self._execute_command("getProgramInfo")
    
    def get_settings(self):
        """Get controller settings"""
        return self._execute_command("getSettings")
    
    def get_schedule(self):
        """Get program schedule information"""
        try:
            # Get basic schedule info
            schedule_data = self._execute_command("RetrieveScheduleRequest", 0)
            return schedule_data
        except Exception as e:
            # Fallback to program info if schedule request fails
            return self.get_program_info()
    
    def start_zone(self, zone_id, duration_minutes):
        """Start irrigation for a specific zone"""
        if not (1 <= zone_id <= 16):
            raise ValueError("Zone ID must be between 1 and 16")
        if not (1 <= duration_minutes <= 60):
            raise ValueError("Duration must be between 1 and 60 minutes")
        
        return self._execute_command("ManuallyRunStationRequest", zone_id, duration_minutes)
    
    def stop_irrigation(self):
        """Stop all irrigation"""
        return self._execute_command("StopIrrigationRequest")
    
    def test_connection(self):
        """Test connection to controller"""
        try:
            model_info = self.get_model_version()
            return {
                "success": True,
                "message": "Connected successfully",
                "model_info": model_info
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
