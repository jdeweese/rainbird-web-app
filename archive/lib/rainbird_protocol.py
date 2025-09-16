#!/usr/bin/env python3
"""
RainBird Protocol Handler
Handles command encoding/decoding and response processing
"""

class RainBirdProtocol:
    """RainBird protocol command definitions and processing"""
    
    COMMANDS = {
        "ModelAndVersionRequest": {"command": "02", "response": "82", "length": 1},
        "AvailableStationsRequest": {"command": "03", "response": "83", "length": 2},
        "CurrentTimeRequest": {"command": "10", "response": "90", "length": 1},
        "CurrentDateRequest": {"command": "12", "response": "92", "length": 1},
        "CurrentIrrigationStateRequest": {"command": "48", "response": "C8", "length": 1},
        "CurrentRainSensorStateRequest": {"command": "3E", "response": "BE", "length": 1},
        "ManuallyRunStationRequest": {"command": "39", "response": "B9", "length": 3},
        "StopIrrigationRequest": {"command": "40", "response": "C0", "length": 1},
        "RetrieveScheduleRequest": {"command": "20", "response": "A0", "length": 2},
    }
    
    # JSON-RPC methods for local API
    LOCAL_METHODS = [
        "getProgramInfo",
        "getSettings", 
        "getWifiParams",
        "getNetworkStatus",
        "getServerMode"
    ]
    
    @classmethod
    def get_command(cls, command_name):
        """Get command definition by name"""
        return cls.COMMANDS.get(command_name)
    
    @classmethod
    def is_local_method(cls, method_name):
        """Check if method is a local JSON-RPC method"""
        return method_name in cls.LOCAL_METHODS
    
    @classmethod
    def build_request(cls, command_name, *params):
        """Build JSON-RPC request for RainBird controller"""
        # Handle local methods differently
        if cls.is_local_method(command_name):
            return {
                "jsonrpc": "2.0",
                "method": command_name,
                "params": {},
                "id": 1
            }
        
        command_data = cls.get_command(command_name)
        if not command_data:
            raise ValueError(f"Unknown command: {command_name}")
        
        # Build hex command string
        hex_command = command_data["command"]
        for param in params:
            if isinstance(param, int):
                hex_command += f"{param:02X}"
            else:
                hex_command += str(param)
        
        if len(hex_command) // 2 != command_data["length"]:
            raise ValueError("Invalid parameters for command")
        
        return {
            "jsonrpc": "2.0",
            "method": "tunnelSip",
            "params": {
                "data": hex_command,
                "length": command_data["length"]
            },
            "id": 1
        }
    
    @classmethod
    def process_response(cls, response_data, command_name):
        """Process response from RainBird controller"""
        if cls.is_local_method(command_name):
            # Local methods return data directly
            return {
                "command": command_name,
                "data": response_data.get("result", {}),
                "raw_result": response_data
            }
        
        command_data = cls.get_command(command_name)
        if not command_data:
            raise ValueError(f"Unknown command: {command_name}")
        
        if response_data.get("error"):
            error = response_data["error"]
            raise Exception(f"Controller error {error.get('code')}: {error.get('message')}")
        
        result = response_data.get("result", {})
        hex_data = result.get("data", "")
        
        # Verify response code for tunnelSip commands
        expected_code = command_data["response"]
        if not hex_data.startswith(expected_code):
            raise Exception(f"Unexpected response code. Expected {expected_code}, got {hex_data[:2]}")
        
        return {
            "command": command_name,
            "hex_data": hex_data,
            "length": result.get("length", 0),
            "raw_result": result
        }
