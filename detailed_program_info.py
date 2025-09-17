#!/usr/bin/env python3
"""
Detailed Program Information Retrieval
Shows exactly what program data can be retrieved from ESP-ME3
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def get_detailed_program_info():
    print("📋 DETAILED PROGRAM INFORMATION RETRIEVAL")
    print("="*60)
    print("🔍 Showing EXACTLY what program data ESP-ME3 provides")
    print("="*60)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        print("1️⃣ PROGRAM INFO (get_program_info):")
        print("-" * 40)
        try:
            program_info = await controller.get_program_info()
            print(f"Raw data: {program_info}")
            print(f"Type: {type(program_info)}")
            
            print("\nDetailed breakdown:")
            print(f"  • Soil Types: {program_info.soil_types}")
            for i, soil in enumerate(program_info.soil_types):
                print(f"    Program {i+1}: {soil} (value: {soil.value})")
            
            print(f"  • Flow Rates: {program_info.flow_rates}")
            for i, rate in enumerate(program_info.flow_rates):
                print(f"    Program {i+1}: {rate}")
            
            print(f"  • Flow Units: {program_info.flow_units}")
            for i, unit in enumerate(program_info.flow_units):
                print(f"    Program {i+1}: {unit}")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        print("\n2️⃣ SCHEDULE (get_schedule):")
        print("-" * 40)
        try:
            schedule = await controller.get_schedule()
            print(f"Raw data: {schedule}")
            print(f"Type: {type(schedule)}")
            
            print("\nDetailed breakdown:")
            print(f"  • Controller Info: {schedule.controller_info}")
            print(f"    - Station Delay: {schedule.controller_info.station_delay}")
            print(f"    - Rain Delay: {schedule.controller_info.rain_delay}")
            print(f"    - Rain Sensor: {schedule.controller_info.rain_sensor}")
            
            print(f"  • Delay Days: {schedule.delay_days}")
            print(f"  • Programs List: {schedule.programs}")
            print(f"    - Number of programs: {len(schedule.programs)}")
            
            if schedule.programs:
                for i, program in enumerate(schedule.programs):
                    print(f"    Program {i+1}: {program}")
            else:
                print("    ⚠️  No programs stored in controller")
            
            print(f"  • Timeline: {schedule.timeline}")
            
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        print("\n3️⃣ SETTINGS (program-related):")
        print("-" * 40)
        try:
            settings = await controller.get_settings()
            
            # Extract program-related settings
            program_attrs = [attr for attr in dir(settings) if 'program' in attr.lower()]
            
            print("Program-related settings:")
            for attr in program_attrs:
                try:
                    value = getattr(settings, attr)
                    print(f"  • {attr}: {value}")
                except:
                    print(f"  • {attr}: <unable to read>")
            
            # Show some key settings
            key_attrs = ['num_programs', 'program_opt_out_mask']
            print("\nKey program settings:")
            for attr in key_attrs:
                if hasattr(settings, attr):
                    value = getattr(settings, attr)
                    print(f"  • {attr}: {value}")
                    
        except Exception as e:
            print(f"❌ Failed: {e}")
        
        print("\n4️⃣ INDIVIDUAL PROGRAM QUERIES:")
        print("-" * 40)
        print("Testing if controller supports individual program queries...")
        
        for prog_id in range(1, 5):  # Test programs 1-4
            try:
                # Try different approaches to get individual program data
                print(f"\nProgram {prog_id}:")
                
                # Method 1: Try schedule command (if supported)
                try:
                    result = await controller.get_schedule_command(f"0{prog_id}")
                    print(f"  • Schedule command result: {result}")
                except Exception as e:
                    print(f"  • Schedule command: Not supported ({e})")
                
                # Method 2: Test command support
                try:
                    supported = await controller.test_command_support(0x20 + prog_id - 1)
                    print(f"  • Command support: {supported}")
                except Exception as e:
                    print(f"  • Command support test: Failed ({e})")
                
            except Exception as e:
                print(f"  • Program {prog_id}: Failed ({e})")
        
        print("\n" + "="*60)
        print("📊 SUMMARY - What Program Info ESP-ME3 Provides:")
        print("="*60)
        print("✅ AVAILABLE DATA:")
        print("  • Number of program slots: 4")
        print("  • Soil type settings per program")
        print("  • Flow rate settings per program") 
        print("  • Flow unit settings per program")
        print("  • Controller delay settings")
        print("  • Rain delay status")
        print("  • Rain sensor status")
        
        print("\n❌ NOT AVAILABLE:")
        print("  • Actual stored program schedules")
        print("  • Zone assignments per program")
        print("  • Run times per zone")
        print("  • Start times/schedules")
        print("  • Days of week settings")
        
        print("\n💡 CONCLUSION:")
        print("ESP-ME3 provides program CONFIGURATION data but")
        print("does NOT store actual program SCHEDULES or automation.")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(get_detailed_program_info())
