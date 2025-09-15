#!/usr/bin/env python3
"""
RainBird Controller Interface
High-level interface for RainBird controller operations
"""

from .rainbird_connection import RainBirdConnection
from .rainbird_protocol import RainBirdProtocol
from .data_formatter import RainBirdFormatter

class RainBirdController:
    """High-level RainBird controller interface"""
    
    def __init__(self, ip_address, password):
        self.ip_address = ip_address
        self.password = password
        self.connection = RainBirdConnection()
        self.protocol = RainBirdProtocol()
        self.formatter = RainBirdFormatter()
    
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
