#!/usr/bin/env python3
"""
Show raw output from get_programs functions
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def show_raw_output():
    print("🔍 RAW OUTPUT FROM GET_PROGRAMS FUNCTIONS")
    print("="*60)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        print("1️⃣ RAW get_program_info() OUTPUT:")
        print("-" * 40)
        program_info = await controller.get_program_info()
        print(f"Type: {type(program_info)}")
        print(f"Raw: {program_info}")
        print(f"Repr: {repr(program_info)}")
        
        print("\n2️⃣ RAW get_schedule() OUTPUT:")
        print("-" * 40)
        schedule = await controller.get_schedule()
        print(f"Type: {type(schedule)}")
        print(f"Raw: {schedule}")
        print(f"Repr: {repr(schedule)}")
        
        print("\n3️⃣ RAW get_settings() OUTPUT (program-related):")
        print("-" * 40)
        settings = await controller.get_settings()
        print(f"Type: {type(settings)}")
        print(f"Raw: {settings}")
        
        print("\n4️⃣ DETAILED BREAKDOWN:")
        print("-" * 40)
        
        print("program_info attributes:")
        for attr in ['soil_types', 'flow_rates', 'flow_units']:
            value = getattr(program_info, attr)
            print(f"  {attr}: {value} (type: {type(value)})")
        
        print("\nschedule attributes:")
        for attr in ['controller_info', 'programs', 'delay_days', 'timeline']:
            value = getattr(schedule, attr)
            print(f"  {attr}: {value} (type: {type(value)})")
        
        print("\nschedule.controller_info attributes:")
        for attr in ['station_delay', 'rain_delay', 'rain_sensor']:
            value = getattr(schedule.controller_info, attr)
            print(f"  {attr}: {value} (type: {type(value)})")
        
        print("\nsettings program-related attributes:")
        program_attrs = ['num_programs', 'program_opt_out_mask']
        for attr in program_attrs:
            if hasattr(settings, attr):
                value = getattr(settings, attr)
                print(f"  {attr}: {value} (type: {type(value)})")
        
        print("\n5️⃣ PROGRAMS LIST DETAILS:")
        print("-" * 40)
        print(f"schedule.programs: {schedule.programs}")
        print(f"Length: {len(schedule.programs)}")
        print(f"Type: {type(schedule.programs)}")
        
        if schedule.programs:
            for i, program in enumerate(schedule.programs):
                print(f"\nProgram {i}:")
                print(f"  Raw: {program}")
                print(f"  Type: {type(program)}")
                print(f"  Attributes: {dir(program)}")
        else:
            print("No programs in list")
        
        print("\n6️⃣ TIMELINE DETAILS:")
        print("-" * 40)
        timeline = schedule.timeline
        print(f"Timeline: {timeline}")
        print(f"Type: {type(timeline)}")
        print(f"Methods: {[m for m in dir(timeline) if not m.startswith('_')]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(show_raw_output())
