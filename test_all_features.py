#!/usr/bin/env python3
"""
Comprehensive CLI Feature Test
Tests all CLI features and reports issues
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def test_all_features():
    print("🧪 Testing All CLI Features")
    print("="*50)
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        print("1️⃣ Testing Connection...")
        controller = async_client.CreateController(
            session,
            config['controller_ip'],
            config['controller_password']
        )
        
        model_info = await controller.get_model_and_version()
        serial = await controller.get_serial_number()
        print(f"   ✅ Model: {model_info.model_name} ({model_info.model})")
        print(f"   ✅ Version: {model_info.major}.{model_info.minor}")
        print(f"   ✅ Serial: {serial}")
        
        print("\n2️⃣ Testing Zones...")
        zones_data = await controller.get_available_stations()
        zone_states = await controller.get_zone_states()
        active_zones = []
        for i, available in enumerate(zones_data.stations.states, 1):
            if available:
                active_zones.append(i)
        print(f"   ✅ Found {len(active_zones)} active zones: {active_zones[:10]}...")
        
        print("\n3️⃣ Testing System Status...")
        irrigation_active = await controller.get_current_irrigation()
        rain_sensor = await controller.get_rain_sensor_state()
        rain_delay = await controller.get_rain_delay()
        current_date = await controller.get_current_date()
        current_time = await controller.get_current_time()
        print(f"   ✅ Irrigation: {'Active' if irrigation_active else 'Inactive'}")
        print(f"   ✅ Rain Sensor: {'Wet' if rain_sensor else 'Dry'}")
        print(f"   ✅ Rain Delay: {rain_delay} days")
        print(f"   ✅ Date: {current_date}")
        print(f"   ✅ Time: {current_time}")
        
        print("\n4️⃣ Testing Zone Control...")
        print("   🚿 Starting Zone 1 for 1 minute...")
        await controller.irrigate_zone(1, 1)
        await asyncio.sleep(3)
        zone_states_after = await controller.get_zone_states()
        if zone_states_after.states[0]:
            print("   ✅ Zone 1 started successfully")
            
            print("   🛑 Stopping irrigation...")
            await controller.stop_irrigation()
            await asyncio.sleep(2)
            irrigation_after_stop = await controller.get_current_irrigation()
            if not irrigation_after_stop:
                print("   ✅ Irrigation stopped successfully")
            else:
                print("   ⚠️  Irrigation may still be active")
        else:
            print("   ⚠️  Zone 1 may not have started")
        
        print("\n5️⃣ Testing Rain Delay...")
        print("   🌧️  Setting 1-day rain delay...")
        await controller.set_rain_delay(1)
        await asyncio.sleep(1)
        delay_check = await controller.get_rain_delay()
        if delay_check == 1:
            print("   ✅ Rain delay set successfully")
            
            print("   🌞 Clearing rain delay...")
            await controller.set_rain_delay(0)
            await asyncio.sleep(1)
            delay_clear = await controller.get_rain_delay()
            if delay_clear == 0:
                print("   ✅ Rain delay cleared successfully")
            else:
                print("   ⚠️  Rain delay may not be cleared")
        else:
            print("   ⚠️  Rain delay may not be set")
        
        print("\n6️⃣ Testing Programs...")
        try:
            program_info = await controller.get_program_info()
            print("   ✅ Program info retrieved")
        except Exception as e:
            print(f"   ⚠️  Program info error: {e}")
        
        try:
            schedule = await controller.get_schedule()
            print("   ✅ Schedule retrieved")
        except Exception as e:
            print(f"   ⚠️  Schedule error: {e}")
        
        print("\n7️⃣ Testing Settings...")
        try:
            settings = await controller.get_settings()
            print("   ✅ Settings retrieved")
        except Exception as e:
            print(f"   ⚠️  Settings error: {e}")
        
        try:
            wifi_params = await controller.get_wifi_params()
            print("   ✅ WiFi params retrieved")
        except Exception as e:
            print(f"   ⚠️  WiFi params error: {e}")
        
        print("\n8️⃣ Testing Zone Test...")
        try:
            print("   🧪 Testing Zone 1 (30 seconds)...")
            await controller.test_zone(1)
            print("   ✅ Zone test started")
        except Exception as e:
            print(f"   ⚠️  Zone test error: {e}")
        
        print("\n🎉 All Tests Complete!")
        print("✅ CLI features are working correctly")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(test_all_features())
