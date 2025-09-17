#!/usr/bin/env python3
"""
Test alternative program retrieval methods
Your apps might be using different API calls
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def test_alternative_program_calls():
    print("🔍 TESTING ALTERNATIVE PROGRAM RETRIEVAL METHODS")
    print("="*60)
    print("💡 Your apps can retrieve programs - let's find the right API call")
    print("="*60)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        # Test 1: get_schedule_and_settings (cloud-based)
        print("\n1️⃣ TESTING get_schedule_and_settings():")
        try:
            # This might need a stick_id - let's try to get it first
            serial = await controller.get_serial_number()
            result = await controller.get_schedule_and_settings(serial)
            print(f"✅ Success: {result}")
            
            if hasattr(result, 'programs') and result.programs:
                print(f"📋 Found {len(result.programs)} programs!")
                for i, program in enumerate(result.programs):
                    print(f"   Program {i+1}: {program}")
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        # Test 2: Individual schedule commands
        print("\n2️⃣ TESTING individual schedule commands:")
        for cmd in ['01', '02', '03', '04']:  # Program 1-4
            try:
                result = await controller.get_schedule_command(cmd)
                print(f"✅ Schedule command {cmd}: {result}")
            except Exception as e:
                print(f"❌ Schedule command {cmd} failed: {e}")
        
        # Test 3: Test different command IDs
        print("\n3️⃣ TESTING command support for program-related commands:")
        program_commands = [0x20, 0x21, 0x22, 0x23, 0x30, 0x31, 0x32, 0x33, 0x38, 0x39]
        for cmd_id in program_commands:
            try:
                supported = await controller.test_command_support(cmd_id)
                print(f"Command 0x{cmd_id:02X}: {'✅ Supported' if supported else '❌ Not supported'}")
            except Exception as e:
                print(f"Command 0x{cmd_id:02X}: ❌ Error: {e}")
        
        # Test 4: Try RPC methods
        print("\n4️⃣ TESTING RPC methods:")
        rpc_methods = ['getPrograms', 'getSchedule', 'getProgramInfo', 'getSettings']
        for method in rpc_methods:
            try:
                result = await controller.test_rpc_support(method)
                print(f"RPC {method}: ✅ {result}")
            except Exception as e:
                print(f"RPC {method}: ❌ {e}")
        
        # Test 5: Check if there are other schedule-related methods
        print("\n5️⃣ CHECKING all controller methods for 'program' or 'schedule':")
        all_methods = [method for method in dir(controller) if not method.startswith('_')]
        program_methods = [m for m in all_methods if 'program' in m.lower() or 'schedule' in m.lower()]
        
        print(f"Found methods: {program_methods}")
        
        for method_name in program_methods:
            if method_name not in ['get_program_info', 'get_schedule', 'get_schedule_command', 'get_schedule_and_settings']:
                try:
                    method = getattr(controller, method_name)
                    print(f"Method {method_name}: {method}")
                    # Don't call it, just show it exists
                except Exception as e:
                    print(f"Method {method_name}: Error accessing - {e}")
        
        # Test 6: Try weather and status (might contain program info)
        print("\n6️⃣ TESTING weather_and_status (might contain program data):")
        try:
            serial = await controller.get_serial_number()
            result = await controller.get_weather_and_status(serial, "US", "98052")
            print(f"✅ Weather and status: {result}")
            
            # Check if it has program-related data
            if hasattr(result, '__dict__'):
                attrs = [attr for attr in dir(result) if 'program' in attr.lower()]
                if attrs:
                    print(f"Program-related attributes: {attrs}")
                    for attr in attrs:
                        value = getattr(result, attr)
                        print(f"   {attr}: {value}")
        except Exception as e:
            print(f"❌ Weather and status failed: {e}")
        
        print("\n" + "="*60)
        print("🎯 ANALYSIS: Which method might your apps be using?")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(test_alternative_program_calls())
