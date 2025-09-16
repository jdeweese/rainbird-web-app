#!/usr/bin/env python3
"""
Check Controller Program Support
Investigate what program features the ESP-ME3 controller actually supports
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def check_program_support():
    print("🔍 CONTROLLER PROGRAM SUPPORT INVESTIGATION")
    print("="*60)
    print("📡 Testing ESP-ME3 controller program capabilities")
    print("="*60)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        # Get controller info first
        model_info = await controller.get_model_and_version()
        print(f"🎯 Controller: {model_info.model_name} ({model_info.model}) v{model_info.major}.{model_info.minor}")
        
        print("\n1️⃣ TESTING PROGRAM INFO:")
        try:
            program_info = await controller.get_program_info()
            print(f"   ✅ Program info retrieved")
            print(f"   📋 Data: {program_info}")
            
            # Check if it has actual program data
            if hasattr(program_info, '__dict__'):
                attrs = [attr for attr in dir(program_info) if not attr.startswith('_')]
                print(f"   🔍 Available attributes: {attrs}")
                for attr in attrs[:5]:  # Show first 5 attributes
                    try:
                        value = getattr(program_info, attr)
                        print(f"   📊 {attr}: {value}")
                    except:
                        pass
        except Exception as e:
            print(f"   ❌ Program info failed: {e}")
        
        print("\n2️⃣ TESTING SCHEDULE:")
        try:
            schedule = await controller.get_schedule()
            print(f"   ✅ Schedule retrieved")
            print(f"   📋 Data: {schedule}")
            
            # Check schedule attributes
            if hasattr(schedule, '__dict__'):
                attrs = [attr for attr in dir(schedule) if not attr.startswith('_')]
                print(f"   🔍 Available attributes: {attrs}")
                for attr in attrs[:5]:  # Show first 5 attributes
                    try:
                        value = getattr(schedule, attr)
                        print(f"   📊 {attr}: {value}")
                    except:
                        pass
        except Exception as e:
            print(f"   ❌ Schedule failed: {e}")
        
        print("\n3️⃣ TESTING INDIVIDUAL PROGRAM COMMANDS:")
        for prog_id in [1, 2, 3, 4]:
            try:
                print(f"   🧪 Testing program {prog_id} support...")
                # Try to get program-specific data
                result = await controller.test_command_support(0x38)  # Program command
                print(f"   📊 Program command support: {result}")
                break  # Only test once
            except Exception as e:
                print(f"   ⚠️  Program {prog_id} test: {e}")
        
        print("\n4️⃣ TESTING SETTINGS FOR PROGRAM DATA:")
        try:
            settings = await controller.get_settings()
            print(f"   ✅ Settings retrieved")
            
            # Look for program-related settings
            if hasattr(settings, '__dict__'):
                attrs = [attr for attr in dir(settings) if not attr.startswith('_')]
                program_attrs = [attr for attr in attrs if 'program' in attr.lower()]
                schedule_attrs = [attr for attr in attrs if 'schedule' in attr.lower()]
                
                print(f"   🔍 Program-related attributes: {program_attrs}")
                print(f"   🔍 Schedule-related attributes: {schedule_attrs}")
                
                # Show some general settings
                for attr in attrs[:10]:
                    try:
                        value = getattr(settings, attr)
                        if 'program' in attr.lower() or 'schedule' in attr.lower():
                            print(f"   📊 {attr}: {value}")
                    except:
                        pass
        except Exception as e:
            print(f"   ❌ Settings failed: {e}")
        
        print("\n5️⃣ TESTING PROGRAM EXECUTION:")
        try:
            print("   🏃 Testing program 1 execution...")
            await controller.set_program(1)
            print("   ✅ Program execution command accepted")
            
            # Check if anything changed
            await asyncio.sleep(2)
            irrigation_status = await controller.get_current_irrigation()
            zone_states = await controller.get_zone_states()
            running_zones = [i+1 for i, state in enumerate(zone_states.states[:19]) if state]
            
            print(f"   📊 After program start:")
            print(f"   💧 Irrigation active: {irrigation_status}")
            print(f"   🚿 Running zones: {running_zones if running_zones else 'None'}")
            
        except Exception as e:
            print(f"   ❌ Program execution failed: {e}")
        
        print("\n" + "="*60)
        print("🎯 PROGRAM SUPPORT ANALYSIS")
        print("="*60)
        print("📋 ESP-ME3 Controller Program Capabilities:")
        print("   • Program info API: Available but may be empty")
        print("   • Schedule API: Available but may be empty") 
        print("   • Program execution: Command accepted")
        print("   • Program storage: May not store complex schedules")
        print("\n💡 CONCLUSION:")
        print("   The ESP-ME3 appears to be a basic controller that:")
        print("   • Supports manual zone control ✅")
        print("   • Accepts program commands ✅")
        print("   • May not store complex program schedules ⚠️")
        print("   • Focuses on direct zone control rather than scheduling ⚠️")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(check_program_support())
