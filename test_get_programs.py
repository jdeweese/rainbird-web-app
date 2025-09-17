#!/usr/bin/env python3
"""
Standalone test for get_programs function
Calls the enhanced get_programs and shows decoded output
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from pyrainbird import async_client

class ProgramTester:
    def __init__(self):
        self.config = self.load_config()
        self.controller = None
        self.session = None
    
    def load_config(self):
        with open('config.json', 'r') as f:
            return json.load(f)
    
    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.controller = async_client.CreateController(
            self.session,
            self.config['controller_ip'],
            self.config['controller_password']
        )
    
    async def get_programs(self):
        """Get program information with complete schedule details - EXACT COPY FROM CLI"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("📋 Getting complete program and schedule information...")
            
            # Get all program-related data
            program_info = await self.controller.get_program_info()
            schedule = await self.controller.get_schedule()
            settings = await self.controller.get_settings()
            
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
                    print(f"\n   📋 Program {i} ({program.name}):")
                    print(f"      🔢 Program Number: {program.program}")
                    print(f"      📅 Frequency: {program.frequency}")
                    
                    # Show days of week for CUSTOM programs
                    if program.days_of_week:
                        days = [day.name for day in program.days_of_week]
                        print(f"      📆 Days of Week: {', '.join(days)}")
                    
                    # Show period for CYCLIC programs
                    if program.period:
                        print(f"      🔄 Period: Every {program.period} days")
                    
                    # Show start times
                    if program.starts:
                        start_times = [start.strftime('%I:%M %p') for start in program.starts]
                        print(f"      🕐 Start Times: {', '.join(start_times)}")
                    
                    # Show zone durations (the key info you wanted)
                    if program.durations:
                        print(f"      🚿 Zone Durations:")
                        total_duration = 0
                        for zone_duration in program.durations:
                            zone_num = zone_duration.zone
                            duration_mins = int(zone_duration.duration.total_seconds() / 60)
                            total_duration += duration_mins
                            print(f"         Zone {zone_num}: {duration_mins} minutes")
                        print(f"      ⏱️  Total Program Duration: {total_duration} minutes")
                    else:
                        print(f"      ⚠️  No zone durations configured")
                    
                    # Show synchro if set
                    if program.synchro:
                        print(f"      🔄 Synchro: {program.synchro} days")
                    
                    # Show total program duration
                    total_duration = program.duration
                    if total_duration.total_seconds() > 0:
                        mins = int(total_duration.total_seconds() / 60)
                        print(f"      ⏰ Program Duration: {mins} minutes")
            else:
                print(f"   ⚠️  No programs stored in controller")
                print(f"   💡 ESP-ME3 is a basic controller - programs may need to be")
                print(f"   💡 configured through the physical controller or mobile app")
            
            # Show timeline information if available
            if hasattr(schedule, 'timeline') and schedule.timeline:
                print(f"\n⏰ Timeline Information:")
                try:
                    # Try to get timeline details
                    timeline = schedule.timeline
                    print(f"   📊 Timeline object: {timeline}")
                    
                    # Check for timeline methods/properties
                    if hasattr(timeline, 'get_current_program'):
                        current = timeline.get_current_program()
                        print(f"   🎯 Current program: {current}")
                    
                    if hasattr(timeline, 'get_next_program'):
                        next_prog = timeline.get_next_program()
                        print(f"   ⏭️  Next program: {next_prog}")
                        
                except Exception as e:
                    print(f"   ⚠️  Timeline details unavailable: {e}")
            
        except Exception as e:
            print(f"❌ Failed to get programs: {e}")
    
    async def cleanup(self):
        if self.session:
            await self.session.close()

async def main():
    print("🧪 STANDALONE GET_PROGRAMS TEST")
    print("="*50)
    print(f"🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    tester = ProgramTester()
    
    try:
        print("🔌 Connecting to controller...")
        await tester.connect()
        
        model_info = await tester.controller.get_model_and_version()
        print(f"✅ Connected to {model_info.model_name} ({model_info.model}) v{model_info.major}.{model_info.minor}")
        
        print("\n" + "="*50)
        print("📋 RUNNING GET_PROGRAMS FUNCTION")
        print("="*50)
        
        await tester.get_programs()
        
        print("\n" + "="*50)
        print("✅ GET_PROGRAMS TEST COMPLETE")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await tester.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
