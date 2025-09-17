#!/usr/bin/env python3
"""
Check what program data actually returns from controller
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def check_program_data():
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        print("🔍 CHECKING ACTUAL PROGRAM DATA RETURNED")
        print("="*50)
        
        # Get schedule data
        schedule = await controller.get_schedule()
        
        print(f"Schedule object: {schedule}")
        print(f"Schedule type: {type(schedule)}")
        print(f"Programs list: {schedule.programs}")
        print(f"Programs length: {len(schedule.programs)}")
        
        # Check all schedule attributes
        print(f"\nSchedule attributes:")
        for attr in dir(schedule):
            if not attr.startswith('_'):
                try:
                    value = getattr(schedule, attr)
                    print(f"  {attr}: {value} (type: {type(value)})")
                except:
                    print(f"  {attr}: <unable to read>")
        
        # If programs exist, examine them
        if schedule.programs:
            print(f"\nProgram details:")
            for i, program in enumerate(schedule.programs):
                print(f"\nProgram {i+1}:")
                print(f"  Raw: {program}")
                print(f"  Type: {type(program)}")
                
                # Check all program attributes
                for attr in dir(program):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(program, attr)
                            print(f"    {attr}: {value}")
                        except:
                            print(f"    {attr}: <unable to read>")
        
        # Check timeline for program data
        if hasattr(schedule, 'timeline'):
            print(f"\nTimeline investigation:")
            timeline = schedule.timeline
            print(f"Timeline: {timeline}")
            
            # Try timeline methods
            try:
                current = timeline.now()
                print(f"Timeline now: {current}")
            except Exception as e:
                print(f"Timeline now failed: {e}")
            
            try:
                today = timeline.today()
                print(f"Timeline today: {today}")
            except Exception as e:
                print(f"Timeline today failed: {e}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(check_program_data())
