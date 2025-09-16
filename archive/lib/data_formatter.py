#!/usr/bin/env python3
"""
Enhanced Data Formatter for RainBird Controller
Comprehensive parsing and formatting of controller responses
"""

import time
from datetime import datetime

class RainBirdFormatter:
    """Enhanced formatter for RainBird controller data"""
    
    @staticmethod
    def format_model_version(response_data):
        """Format model and version response"""
        if isinstance(response_data, dict) and 'data' in response_data:
            data = response_data['data']
        else:
            data = response_data
        
        if data and len(data) >= 10:
            return {
                'model_id': data[2:4],
                'version': data[4:6],
                'revision': data[6:8],
                'raw_data': data
            }
        return {'raw_data': data}
    
    @staticmethod
    def parse_available_stations(data):
        """Parse available stations from controller response"""
        if not data or len(data) < 4:
            return []
        
        # Remove '90' prefix if present
        if data.startswith('90'):
            zone_mask = data[2:]
        else:
            zone_mask = data
        
        zones = []
        for i in range(0, len(zone_mask), 2):
            if i + 1 < len(zone_mask):
                byte_hex = zone_mask[i:i+2]
                try:
                    byte_val = int(byte_hex, 16)
                    # Check each bit in the byte
                    for bit in range(8):
                        if byte_val & (1 << bit):
                            zone_num = (i // 2) * 8 + bit + 1
                            zones.append(zone_num)
                except ValueError:
                    continue
        
        return sorted(zones)
    
    @staticmethod
    def parse_irrigation_state(data):
        """Parse current irrigation state"""
        if not data or len(data) < 4:
            return {'active': False, 'zone': None, 'time_remaining': 0}
        
        # Parse irrigation state (C8 indicates active irrigation)
        if data.startswith('C8'):
            zone_byte = data[2:4] if len(data) >= 4 else '00'
            try:
                zone_id = int(zone_byte, 16)
                
                # Parse time remaining if available
                time_remaining = 0
                if len(data) >= 8:
                    time_hex = data[4:8]
                    try:
                        time_remaining = int(time_hex, 16)
                    except ValueError:
                        time_remaining = 0
                
                return {
                    'active': True,
                    'zone': zone_id if zone_id > 0 else None,
                    'time_remaining': time_remaining,
                    'raw_data': data
                }
            except ValueError:
                pass
        
        return {'active': False, 'zone': None, 'time_remaining': 0, 'raw_data': data}
    
    @staticmethod
    def parse_rain_sensor(data):
        """Parse rain sensor status"""
        if not data:
            return {'active': False, 'raw_data': data}
        
        # Rain sensor active if data contains '01'
        active = '01' in data
        return {
            'active': active,
            'status': 'active' if active else 'inactive',
            'raw_data': data
        }
    
    @staticmethod
    def parse_rain_delay(data):
        """Parse rain delay status"""
        if not data or len(data) < 2:
            return {'hours': 0, 'active': False, 'raw_data': data}
        
        try:
            hours = int(data[:2], 16)
            return {
                'hours': hours,
                'active': hours > 0,
                'raw_data': data
            }
        except ValueError:
            return {'hours': 0, 'active': False, 'raw_data': data}
    
    @staticmethod
    def parse_program_data(data):
        """Parse program configuration data"""
        if not data:
            return None
        
        # Basic program data parsing
        return {
            'enabled': True,
            'schedule': 'Not parsed',
            'zones': [],
            'raw_data': data
        }
    
    @staticmethod
    def parse_water_budget(data):
        """Parse water budget percentage"""
        if not data or len(data) < 2:
            return {'percentage': 100, 'raw_data': data}
        
        try:
            percentage = int(data[:2], 16)
            return {
                'percentage': percentage,
                'raw_data': data
            }
        except ValueError:
            return {'percentage': 100, 'raw_data': data}
    
    @staticmethod
    def parse_current_time(data):
        """Parse controller current time"""
        if not data or len(data) < 12:
            return {'timestamp': None, 'raw_data': data}
        
        try:
            return {
                'timestamp': time.time(),
                'formatted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'raw_data': data
            }
        except:
            return {'timestamp': None, 'raw_data': data}
    
    @staticmethod
    def format_serial_number(response_data):
        """Format serial number response"""
        if isinstance(response_data, dict) and 'data' in response_data:
            data = response_data['data']
        else:
            data = response_data
        
        return {
            'serial_number': data,
            'raw_data': data
        }
        
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
