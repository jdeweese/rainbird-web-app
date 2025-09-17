#!/usr/bin/env python3
"""
Test Enhanced Program Display
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def test_enhanced_programs():
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        print("📋 Getting complete program and schedule information...")
        
        # Get all program-related data
        program_info = await controller.get_program_info()
        schedule = await controller.get_schedule()
        settings = await controller.get_settings()
        
        print(f"✅ Controller Program Analysis:")
        print(f"   📊 Program slots available: {getattr(settings, 'num_programs', 'Unknown')}")
        print(f"   🔧 Program opt-out mask: {getattr(settings, 'program_opt_out_mask', 'Unknown')}")
        
        # Show program configuration
        print(f"\n📋 Program Configuration:")
        for i in range(len(program_info.soil_types)):
            soil_type = program_info.soil_types[i]
            flow_rate = program_info.flow_rates[i]
            flow_unit = program_info.flow_units[i]
            
            print(f"   Program {i+1}:")
            print(f"     🌱 Soil Type: {soil_type} (value: {soil_type.value})")
            print(f"     💧 Flow Rate: {flow_rate}")
            print(f"     📏 Flow Unit: {flow_unit}")
        
        # Show schedule details
        print(f"\n📅 Schedule Information:")
        print(f"   🕐 Station Delay: {schedule.controller_info.station_delay} seconds")
        print(f"   🌧️  Rain Delay: {schedule.controller_info.rain_delay} days")
        print(f"   🌦️  Rain Sensor: {'Active' if schedule.controller_info.rain_sensor else 'Inactive'}")
        print(f"   ⏸️  Current Delay Days: {schedule.delay_days}")
        
        # Iterate through all programs in schedule
        print(f"\n🗓️  Stored Programs: {len(schedule.programs)}")
        if schedule.programs:
            for i, program in enumerate(schedule.programs, 1):
                print(f"\n   📋 Program {i}:")
                print(f"      Raw data: {program}")
                
                # Try to extract program details if available
                if hasattr(program, '__dict__'):
                    for attr in dir(program):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(program, attr)
                                if 'zone' in attr.lower() or 'time' in attr.lower() or 'duration' in attr.lower():
                                    print(f"      {attr}: {value}")
                            except:
                                pass
        else:
            print(f"   ⚠️  No programs stored in controller")
            print(f"   💡 ESP-ME3 is a basic controller - programs may need to be")
            print(f"   💡 configured through the physical controller or mobile app")
        
        # Show timeline information if available
        if hasattr(schedule, 'timeline') and schedule.timeline:
            print(f"\n⏰ Timeline Information:")
            try:
                timeline = schedule.timeline
                print(f"   📊 Timeline object: {timeline}")
                print(f"   📊 Timeline type: {type(timeline)}")
                
                # Check timeline attributes
                timeline_attrs = [attr for attr in dir(timeline) if not attr.startswith('_')]
                print(f"   🔍 Timeline methods: {timeline_attrs[:10]}")
                
            except Exception as e:
                print(f"   ⚠️  Timeline details unavailable: {e}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(test_enhanced_programs())
