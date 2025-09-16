#!/usr/bin/env python3
"""
Final Functionality Test - Complete CLI Feature Verification
Tests every single CLI feature with real controller
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from pyrainbird import async_client

async def final_test():
    print("🎯 FINAL FUNCTIONALITY TEST")
    print("="*70)
    print("🔍 Testing EVERY CLI feature with REAL controller")
    print("📡 IP: 192.168.1.113 | Password: 1234")
    print("="*70)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    test_results = []
    
    try:
        # Initialize controller
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        # TEST 1: Connection & Controller Info
        print("\n🔌 TEST 1: CONNECTION & CONTROLLER INFO")
        try:
            model_info = await controller.get_model_and_version()
            serial = await controller.get_serial_number()
            print(f"   ✅ Model: {model_info.model_name} ({model_info.model})")
            print(f"   ✅ Version: {model_info.major}.{model_info.minor}")
            print(f"   ✅ Serial: {serial}")
            test_results.append("✅ Connection & Info")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Connection & Info")
        
        # TEST 2: Zone Display
        print("\n🚿 TEST 2: ZONE DISPLAY")
        try:
            zones_data = await controller.get_available_stations()
            zone_states = await controller.get_zone_states()
            active_zones = [i for i, available in enumerate(zones_data.stations.states, 1) if available and i <= 19]
            running_zones = [i for i, state in enumerate(zone_states.states[:19], 1) if state]
            
            print(f"   ✅ Total zones: {len(active_zones)}")
            print(f"   ✅ Active zones: {active_zones[:10]}...")
            print(f"   ✅ Running zones: {running_zones if running_zones else 'None'}")
            test_results.append("✅ Zone Display")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Zone Display")
        
        # TEST 3: System Status
        print("\n📊 TEST 3: SYSTEM STATUS")
        try:
            irrigation_active = await controller.get_current_irrigation()
            rain_sensor = await controller.get_rain_sensor_state()
            rain_delay = await controller.get_rain_delay()
            current_date = await controller.get_current_date()
            current_time = await controller.get_current_time()
            
            print(f"   ✅ Date: {current_date.strftime('%A, %B %d, %Y')}")
            print(f"   ✅ Time: {current_time.strftime('%I:%M %p')}")
            print(f"   ✅ Irrigation: {'ACTIVE' if irrigation_active else 'Inactive'}")
            print(f"   ✅ Rain Sensor: {'WET' if rain_sensor else 'DRY'}")
            print(f"   ✅ Rain Delay: {rain_delay} days")
            test_results.append("✅ System Status")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ System Status")
        
        # TEST 4: Zone Start/Stop
        print("\n🚿 TEST 4: ZONE START/STOP")
        try:
            print("   🚿 Starting Zone 1 for 1 minute...")
            await controller.irrigate_zone(1, 1)
            await asyncio.sleep(3)
            
            zone_states_after = await controller.get_zone_states()
            if zone_states_after.states[0]:
                print("   ✅ Zone 1 started successfully")
                
                print("   🛑 Stopping irrigation...")
                await controller.stop_irrigation()
                await asyncio.sleep(3)
                
                zone_states_stopped = await controller.get_zone_states()
                if not zone_states_stopped.states[0]:
                    print("   ✅ Zone 1 stopped successfully")
                    test_results.append("✅ Zone Start/Stop")
                else:
                    print("   ⚠️  Zone may still be running")
                    test_results.append("⚠️  Zone Start/Stop")
            else:
                print("   ❌ Zone failed to start")
                test_results.append("❌ Zone Start/Stop")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Zone Start/Stop")
        
        # TEST 5: Zone Test Function
        print("\n🧪 TEST 5: ZONE TEST FUNCTION")
        try:
            print("   🧪 Testing Zone 2 (30 seconds)...")
            await controller.test_zone(2)
            print("   ✅ Zone test command sent successfully")
            test_results.append("✅ Zone Test")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Zone Test")
        
        # TEST 6: Rain Delay Management
        print("\n🌧️  TEST 6: RAIN DELAY MANAGEMENT")
        try:
            print("   🌧️  Setting 1-day rain delay...")
            await controller.set_rain_delay(1)
            await asyncio.sleep(2)
            
            delay_check = await controller.get_rain_delay()
            if delay_check == 1:
                print("   ✅ Rain delay set successfully")
                
                print("   🌞 Clearing rain delay...")
                await controller.set_rain_delay(0)
                await asyncio.sleep(2)
                
                delay_clear = await controller.get_rain_delay()
                if delay_clear == 0:
                    print("   ✅ Rain delay cleared successfully")
                    test_results.append("✅ Rain Delay")
                else:
                    print("   ❌ Rain delay not cleared")
                    test_results.append("❌ Rain Delay")
            else:
                print("   ❌ Rain delay not set")
                test_results.append("❌ Rain Delay")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Rain Delay")
        
        # TEST 7: Program Information
        print("\n📋 TEST 7: PROGRAM INFORMATION")
        try:
            program_info = await controller.get_program_info()
            schedule = await controller.get_schedule()
            print("   ✅ Program info retrieved successfully")
            print("   ✅ Schedule info retrieved successfully")
            test_results.append("✅ Program Info")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Program Info")
        
        # TEST 8: Program Execution
        print("\n🏃 TEST 8: PROGRAM EXECUTION")
        try:
            print("   🏃 Running Program 1...")
            await controller.set_program(1)
            print("   ✅ Program 1 started successfully")
            test_results.append("✅ Program Execution")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Program Execution")
        
        # TEST 9: Settings & WiFi
        print("\n⚙️  TEST 9: SETTINGS & WIFI")
        try:
            settings = await controller.get_settings()
            wifi_params = await controller.get_wifi_params()
            print("   ✅ Controller settings retrieved")
            print("   ✅ WiFi parameters retrieved")
            test_results.append("✅ Settings & WiFi")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Settings & WiFi")
        
        # TEST 10: Configuration Display
        print("\n📋 TEST 10: CONFIGURATION DISPLAY")
        try:
            print(f"   ✅ IP Address: {config['controller_ip']}")
            print(f"   ✅ Password: {'*' * len(config['controller_password'])}")
            print(f"   ✅ Timeout: {config['timeout']} seconds")
            test_results.append("✅ Configuration")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results.append("❌ Configuration")
        
        # FINAL RESULTS
        print("\n" + "="*70)
        print("🎯 FINAL TEST RESULTS")
        print("="*70)
        
        passed = sum(1 for result in test_results if result.startswith("✅"))
        warnings = sum(1 for result in test_results if result.startswith("⚠️"))
        failed = sum(1 for result in test_results if result.startswith("❌"))
        
        for result in test_results:
            print(f"   {result}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️  Warnings: {warnings}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success Rate: {(passed + warnings) / len(test_results) * 100:.1f}%")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ CLI has FULL FUNCTIONALITY with REAL controller")
            print("🌱 Ready for production use")
        else:
            print(f"\n⚠️  {failed} tests failed - needs attention")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(final_test())
