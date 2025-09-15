#!/usr/bin/env python3
"""
RainBird Data Formatter
Converts hex responses to meaningful data structures
"""

class RainBirdFormatter:
    """Format RainBird controller responses into usable data"""
    
    @staticmethod
    def format_model_version(hex_data):
        """Format ModelAndVersionResponse"""
        if len(hex_data) < 10:
            return {"model": "Unknown", "version": "Unknown"}
        
        # Extract model and version from hex response
        model_code = hex_data[2:6]
        version_code = hex_data[6:10]
        
        return {
            "model": f"Model-{model_code}",
            "version": f"v{version_code}",
            "raw_hex": hex_data
        }
    
    @staticmethod
    def format_available_stations(hex_data):
        """Format AvailableStationsResponse to zone list"""
        if len(hex_data) < 6:
            return {"zones": [], "count": 0}
        
        # Parse station mask from hex
        station_mask = hex_data[2:6]
        mask_int = int(station_mask, 16)
        
        zones = []
        for i in range(16):  # RainBird supports up to 16 zones
            if mask_int & (1 << i):
                zones.append({
                    "id": i + 1,
                    "name": f"Zone {i + 1}",
                    "available": True
                })
        
        return {
            "zones": zones,
            "count": len(zones),
            "mask": station_mask
        }
    
    @staticmethod
    def format_irrigation_state(hex_data):
        """Format CurrentIrrigationStateResponse"""
        if len(hex_data) < 4:
            return {"active": False, "zone": None}
        
        state_code = hex_data[2:4]
        active = state_code != "00"
        
        return {
            "active": active,
            "zone": int(state_code, 16) if active else None,
            "raw_state": state_code
        }
    
    @staticmethod
    def format_rain_sensor(hex_data):
        """Format CurrentRainSensorStateResponse"""
        if len(hex_data) < 4:
            return {"active": False}
        
        sensor_code = hex_data[2:4]
        return {
            "active": sensor_code == "01",
            "raw_state": sensor_code
        }
    
    @staticmethod
    def format_time(hex_data):
        """Format CurrentTimeResponse"""
        if len(hex_data) < 8:
            return {"hour": 0, "minute": 0}
        
        hour = int(hex_data[2:4], 16)
        minute = int(hex_data[4:6], 16)
        
        return {
            "hour": hour,
            "minute": minute,
            "formatted": f"{hour:02d}:{minute:02d}"
        }
    
    @classmethod
    def format_response(cls, response, command_name):
        """Format response based on command type"""
        hex_data = response.get("hex_data", "")
        
        formatters = {
            "ModelAndVersionRequest": cls.format_model_version,
            "AvailableStationsRequest": cls.format_available_stations,
            "CurrentIrrigationStateRequest": cls.format_irrigation_state,
            "CurrentRainSensorStateRequest": cls.format_rain_sensor,
            "CurrentTimeRequest": cls.format_time,
        }
        
        formatter = formatters.get(command_name)
        if formatter:
            return formatter(hex_data)
        
        # Default: return raw data
        return {"raw_hex": hex_data}
