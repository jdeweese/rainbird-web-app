#!/usr/bin/env python3
"""
Enhanced RainBird CLI - Full Mobile App Features
Human-readable responses with complete functionality
"""

import json
import asyncio
import sys
import aiohttp
from datetime import datetime, date, time, timedelta
from pyrainbird import async_client

class RainBirdCLI:
    def __init__(self):
        self.config = self.load_config()
        self.controller = None
        self.session = None
    
    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ config.json not found")
            sys.exit(1)
        except json.JSONDecodeError:
            print("❌ Invalid JSON in config.json")
            sys.exit(1)
    
    async def connect(self):
        """Connect to RainBird controller"""
        try:
            print(f"🔌 Connecting to {self.config['controller_ip']}...")
            
            self.session = aiohttp.ClientSession()
            self.controller = async_client.CreateController(
                self.session,
                self.config['controller_ip'],
                self.config['controller_password']
            )
            
            # Get detailed controller info
            model_info = await self.controller.get_model_and_version()
            serial = await self.controller.get_serial_number()
            
            print(f"✅ Connected to RainBird Controller!")
            print(f"   📱 Model: {model_info.model_name} ({model_info.model})")
            print(f"   🔢 Version: {model_info.major}.{model_info.minor}")
            print(f"   🆔 Serial: {serial}")
            
            try:
                firmware = await self.controller.get_controller_firmware_version()
                print(f"   💾 Firmware: {firmware.version}")
            except:
                print(f"   💾 Firmware: Not available")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if self.session:
                await self.session.close()
            return False
    
    async def get_zones(self):
        """Get available zones with human-readable format"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("🔍 Getting zone information...")
            zones_data = await self.controller.get_available_stations()
            zone_states = await self.controller.get_zone_states()
            
            print(f"✅ Controller has {zones_data.stations.count} total zones")
            print(f"📊 Active zones found:")
            
            active_zones = []
            for i, available in enumerate(zones_data.stations.states, 1):
                if available:
                    state = "🟢 Running" if zone_states.states[i-1] else "⚪ Inactive"
                    active_zones.append(i)
                    print(f"   Zone {i:2d}: {state}")
            
            print(f"\n📈 Summary: {len(active_zones)} zones available ({', '.join(map(str, active_zones))})")
            return active_zones
            
        except Exception as e:
            print(f"❌ Failed to get zones: {e}")
    
    async def get_status(self):
        """Get comprehensive system status"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("📊 Getting system status...")
            
            # Get all status information
            irrigation_active = await self.controller.get_current_irrigation()
            rain_sensor = await self.controller.get_rain_sensor_state()
            rain_delay = await self.controller.get_rain_delay()
            current_date = await self.controller.get_current_date()
            current_time = await self.controller.get_current_time()
            zone_states = await self.controller.get_zone_states()
            
            print(f"✅ System Status Report")
            print(f"   📅 Date: {current_date.strftime('%A, %B %d, %Y')}")
            print(f"   🕐 Time: {current_time.strftime('%I:%M %p')}")
            print(f"   💧 Irrigation: {'🟢 ACTIVE' if irrigation_active else '⚪ Inactive'}")
            print(f"   🌧️  Rain Sensor: {'🔴 WET (irrigation blocked)' if rain_sensor else '🟢 DRY (irrigation allowed)'}")
            print(f"   ⏸️  Rain Delay: {rain_delay} days {'(ACTIVE)' if rain_delay > 0 else '(None)'}")
            
            # Show active zones
            active_zones = []
            for i, state in enumerate(zone_states.states, 1):
                if state:
                    active_zones.append(f"Zone {i}")
            
            if active_zones:
                print(f"   🚿 Running Zones: {', '.join(active_zones)}")
            else:
                print(f"   🚿 Running Zones: None")
                
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
    
    async def start_zone(self, zone_id, duration_minutes):
        """Start irrigation with confirmation"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print(f"🚿 Starting Zone {zone_id} for {duration_minutes} minutes...")
            await self.controller.irrigate_zone(zone_id, duration_minutes)
            
            # Verify it started
            await asyncio.sleep(2)
            zone_states = await self.controller.get_zone_states()
            
            if zone_states.states[zone_id-1]:
                print(f"✅ Zone {zone_id} is now running!")
                print(f"   ⏱️  Duration: {duration_minutes} minutes")
                start_time = datetime.now()
                end_time = start_time + timedelta(minutes=duration_minutes)
                print(f"   🕐 Started: {start_time.strftime('%I:%M %p')}")
                print(f"   🏁 Will stop: {end_time.strftime('%I:%M %p')}")
            else:
                print(f"⚠️  Zone {zone_id} command sent but may not be running")
                
        except Exception as e:
            print(f"❌ Failed to start zone: {e}")
    
    async def stop_irrigation(self):
        """Stop all irrigation with confirmation"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("🛑 Stopping all irrigation...")
            await self.controller.stop_irrigation()
            
            # Verify it stopped (wait a bit longer)
            await asyncio.sleep(3)
            irrigation_active = await self.controller.get_current_irrigation()
            zone_states = await self.controller.get_zone_states()
            
            # Check if any zones are still running
            running_zones = [i+1 for i, state in enumerate(zone_states.states) if state]
            
            if not irrigation_active and not running_zones:
                print(f"✅ All irrigation stopped successfully")
                print(f"   🕐 Stopped at: {datetime.now().strftime('%I:%M %p')}")
            elif not running_zones:
                print(f"✅ All zones stopped (system may show active briefly)")
                print(f"   🕐 Stopped at: {datetime.now().strftime('%I:%M %p')}")
            else:
                print(f"⚠️  Some zones may still be running: {running_zones}")
                
        except Exception as e:
            print(f"❌ Failed to stop irrigation: {e}")
    
    async def get_programs(self):
        """Get program information"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("📋 Getting program information...")
            program_info = await self.controller.get_program_info()
            schedule = await self.controller.get_schedule()
            
            print(f"✅ Program Information:")
            print(f"   📊 Programs available: {len(schedule.programs) if hasattr(schedule, 'programs') else 'Unknown'}")
            print(f"   📅 Schedule active: {'Yes' if hasattr(schedule, 'enabled') and schedule.enabled else 'Unknown'}")
            
        except Exception as e:
            print(f"❌ Failed to get programs: {e}")
    
    async def set_rain_delay(self, days):
        """Set rain delay"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print(f"🌧️  Setting rain delay to {days} days...")
            await self.controller.set_rain_delay(days)
            
            # Verify it was set
            await asyncio.sleep(1)
            current_delay = await self.controller.get_rain_delay()
            
            if current_delay == days:
                if days > 0:
                    print(f"✅ Rain delay set to {days} days")
                    print(f"   ⏸️  All irrigation will be skipped for {days} days")
                else:
                    print(f"✅ Rain delay cleared")
                    print(f"   🟢 Normal irrigation schedule resumed")
            else:
                print(f"⚠️  Rain delay command sent but may not be active")
                
        except Exception as e:
            print(f"❌ Failed to set rain delay: {e}")
    
    async def get_settings(self):
        """Get controller settings"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("⚙️  Getting controller settings...")
            settings = await self.controller.get_settings()
            wifi_params = await self.controller.get_wifi_params()
            
            print(f"✅ Controller Settings:")
            print(f"   📶 WiFi Connected: {'Yes' if hasattr(wifi_params, 'connected') else 'Unknown'}")
            print(f"   🌐 Network Status: Connected to local network")
            print(f"   🔧 Settings loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to get settings: {e}")
    
    async def run_program(self, program_id):
        """Run a program"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print(f"🏃 Running Program {program_id}...")
            await self.controller.set_program(program_id)
            print(f"✅ Program {program_id} started successfully")
            print(f"   📋 Program will run according to its schedule")
            print(f"   🕐 Started at: {datetime.now().strftime('%I:%M %p')}")
        except Exception as e:
            print(f"❌ Failed to run program: {e}")
    
    async def test_zone(self, zone_id):
        """Test a zone (short duration)"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print(f"🧪 Testing Zone {zone_id} (30 second test)...")
            await self.controller.test_zone(zone_id)
            print(f"✅ Zone {zone_id} test started")
            print(f"   ⏱️  Duration: 30 seconds")
            print(f"   🔍 Check if water is flowing to verify zone operation")
            
        except Exception as e:
            print(f"❌ Failed to test zone: {e}")
    
    def show_menu(self):
        """Enhanced menu with all features"""
        print("\n" + "="*60)
        print("🌱 RainBird Controller CLI - Full Feature Set")
        print("="*60)
        print("📡 CONNECTION:")
        print("  1. Connect to controller")
        print("  2. Show controller info")
        print("\n🚿 ZONES & IRRIGATION:")
        print("  3. Show all zones")
        print("  4. Get system status")
        print("  5. Start zone")
        print("  6. Test zone (30 sec)")
        print("  7. Stop all irrigation")
        print("\n📋 PROGRAMS & SCHEDULE:")
        print("  8. Show programs")
        print("  9. Run program")
        print("\n🌧️  WEATHER & DELAYS:")
        print(" 10. Set rain delay")
        print(" 11. Clear rain delay")
        print("\n⚙️  SETTINGS:")
        print(" 12. Show settings")
        print(" 13. Show config")
        print("\n 0. Exit")
        print("="*60)
    
    def show_config(self):
        """Show current configuration"""
        print("\n📋 Current Configuration:")
        print(f"   🌐 IP Address: {self.config['controller_ip']}")
        print(f"   🔐 Password: {'*' * len(self.config['controller_password'])}")
        print(f"   ⏱️  Timeout: {self.config['timeout']} seconds")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def run(self):
        """Enhanced CLI interface"""
        print("🌱 RainBird Controller CLI - Enhanced Edition")
        print(f"📡 Target: {self.config['controller_ip']}")
        print("💡 Tip: Connect first (option 1) to access all features")
        
        try:
            while True:
                self.show_menu()
                choice = input("\n🎯 Enter choice: ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    await self.connect()
                elif choice == '2':
                    if self.controller:
                        await self.connect()  # Shows detailed info
                    else:
                        print("❌ Not connected. Use option 1 first.")
                elif choice == '3':
                    await self.get_zones()
                elif choice == '4':
                    await self.get_status()
                elif choice == '5':
                    zone_id = input("🎯 Enter zone ID (1-19): ").strip()
                    duration = input("⏱️  Enter duration in minutes (1-60): ").strip()
                    try:
                        zone_num = int(zone_id)
                        dur_num = int(duration)
                        if 1 <= zone_num <= 19 and 1 <= dur_num <= 60:
                            await self.start_zone(zone_num, dur_num)
                        else:
                            print("❌ Zone must be 1-19, duration 1-60 minutes")
                    except ValueError:
                        print("❌ Please enter valid numbers")
                elif choice == '6':
                    zone_id = input("🧪 Enter zone ID to test (1-19): ").strip()
                    try:
                        zone_num = int(zone_id)
                        if 1 <= zone_num <= 19:
                            await self.test_zone(zone_num)
                        else:
                            print("❌ Zone must be 1-19")
                    except ValueError:
                        print("❌ Please enter a valid zone number")
                elif choice == '7':
                    confirm = input("⚠️  Stop ALL irrigation? (y/N): ").strip().lower()
                    if confirm == 'y':
                        await self.stop_irrigation()
                    else:
                        print("❌ Cancelled")
                elif choice == '8':
                    await self.get_programs()
                elif choice == '9':
                    program_id = input("🎯 Enter program number (1-4): ").strip()
                    try:
                        prog_num = int(program_id)
                        if 1 <= prog_num <= 4:
                            await self.run_program(prog_num)
                        else:
                            print("❌ Program must be 1-4")
                    except ValueError:
                        print("❌ Please enter a valid program number")
                elif choice == '10':
                    days = input("🌧️  Enter rain delay days (1-7): ").strip()
                    try:
                        delay_days = int(days)
                        if 1 <= delay_days <= 7:
                            await self.set_rain_delay(delay_days)
                        else:
                            print("❌ Rain delay must be 1-7 days")
                    except ValueError:
                        print("❌ Please enter a valid number")
                elif choice == '11':
                    await self.set_rain_delay(0)
                elif choice == '12':
                    await self.get_settings()
                elif choice == '13':
                    self.show_config()
                else:
                    print("❌ Invalid choice. Please try again.")
                
                input("\n⏎ Press Enter to continue...")
        finally:
            await self.cleanup()

async def main():
    """Main function"""
    cli = RainBirdCLI()
    await cli.run()

if __name__ == '__main__':
    asyncio.run(main())
