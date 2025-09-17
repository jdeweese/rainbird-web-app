#!/usr/bin/env python3
"""
Simplified RainBird CLI
Simple zone control with command-line parameters or interactive menu

Usage:
  python3 simple_cli.py                           # Interactive menu
  python3 simple_cli.py --ip IP --password PASS  # Connect only
  python3 simple_cli.py --ip IP --password PASS --zone ZONE --duration MINS  # Run zone
  python3 simple_cli.py --ip IP --password PASS --status  # Get status
  python3 simple_cli.py --help                    # Show help

Examples:
  python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10
  python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status
"""

import asyncio
import aiohttp
import argparse
import sys
from datetime import datetime, timedelta
from pyrainbird import async_client

class SimpleRainBirdCLI:
    def __init__(self, ip=None, password=None):
        self.ip = ip
        self.password = password
        self.controller = None
        self.session = None
        self.zone_start_times = {}  # Track when zones started
    
    async def connect(self):
        """Connect to RainBird controller"""
        try:
            print(f"🔌 Connecting to {self.ip}...")
            self.session = aiohttp.ClientSession()
            self.controller = async_client.CreateController(self.session, self.ip, self.password)
            
            # Test connection
            model_info = await self.controller.get_model_and_version()
            print(f"✅ Connected to {model_info.model_name} ({model_info.model}) v{model_info.major}.{model_info.minor}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def run_zone(self, zone_id, duration_minutes):
        """Start a zone for specified duration"""
        if not self.controller:
            print("❌ Not connected")
            return False
        
        try:
            print(f"🚿 Starting Zone {zone_id} for {duration_minutes} minutes...")
            await self.controller.irrigate_zone(zone_id, duration_minutes)
            
            # Track start time for remaining time calculation
            self.zone_start_times[zone_id] = {
                'start_time': datetime.now(),
                'duration': duration_minutes
            }
            
            # Verify it started
            await asyncio.sleep(2)
            zone_states = await self.controller.get_zone_states()
            
            if zone_states.states[zone_id-1]:
                print(f"✅ Zone {zone_id} started successfully")
                print(f"   ⏱️  Duration: {duration_minutes} minutes")
                print(f"   🕐 Started: {datetime.now().strftime('%I:%M %p')}")
                return True
            else:
                print(f"⚠️  Zone {zone_id} command sent but may not be running")
                return False
        except Exception as e:
            print(f"❌ Failed to start zone: {e}")
            return False
    
    async def get_status(self):
        """Get current irrigation status with remaining time"""
        if not self.controller:
            print("❌ Not connected")
            return
        
        try:
            print("📊 Getting irrigation status...")
            
            # Get current states
            irrigation_active = await self.controller.get_current_irrigation()
            zone_states = await self.controller.get_zone_states()
            current_time = datetime.now()
            
            print(f"✅ System Status:")
            print(f"   💧 Irrigation: {'🟢 ACTIVE' if irrigation_active else '⚪ Inactive'}")
            print(f"   🕐 Current Time: {current_time.strftime('%I:%M %p')}")
            
            # Show running zones with remaining time
            running_zones = []
            for i, state in enumerate(zone_states.states[:19], 1):
                if state:
                    running_zones.append(i)
                    
                    # Calculate remaining time if we tracked the start
                    if i in self.zone_start_times:
                        start_info = self.zone_start_times[i]
                        elapsed = current_time - start_info['start_time']
                        total_duration = timedelta(minutes=start_info['duration'])
                        remaining = total_duration - elapsed
                        
                        if remaining.total_seconds() > 0:
                            remaining_mins = int(remaining.total_seconds() / 60)
                            print(f"   🚿 Zone {i}: Running ({remaining_mins} minutes remaining)")
                        else:
                            print(f"   🚿 Zone {i}: Running (should have stopped)")
                            # Clean up expired tracking
                            del self.zone_start_times[i]
                    else:
                        print(f"   🚿 Zone {i}: Running (unknown remaining time)")
            
            if not running_zones:
                print(f"   🚿 Running Zones: None")
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
    
    async def stop_all(self):
        """Stop all irrigation"""
        if not self.controller:
            print("❌ Not connected")
            return False
        
        try:
            print("🛑 Stopping all irrigation...")
            await self.controller.stop_irrigation()
            
            # Clear tracking
            self.zone_start_times.clear()
            
            await asyncio.sleep(2)
            irrigation_active = await self.controller.get_current_irrigation()
            
            if not irrigation_active:
                print("✅ All irrigation stopped")
                return True
            else:
                print("⚠️  Stop command sent")
                return False
        except Exception as e:
            print(f"❌ Failed to stop irrigation: {e}")
            return False
    
    async def interactive_menu(self):
        """Interactive menu system"""
        print("🌱 Simple RainBird Controller")
        print("="*40)
        
        while True:
            print("\nOptions:")
            print("1. Connect to controller")
            print("2. Run zone")
            print("3. Get status")
            print("4. Stop all irrigation")
            print("0. Exit")
            
            choice = input("\nEnter choice: ").strip()
            
            if choice == '0':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                ip = input("Enter IP address: ").strip()
                password = input("Enter password: ").strip()
                self.ip = ip
                self.password = password
                await self.connect()
            elif choice == '2':
                if not self.controller:
                    print("❌ Connect first (option 1)")
                    continue
                try:
                    zone = int(input("Enter zone number (1-19): ").strip())
                    duration = int(input("Enter duration (minutes): ").strip())
                    if 1 <= zone <= 19 and 1 <= duration <= 60:
                        await self.run_zone(zone, duration)
                    else:
                        print("❌ Zone must be 1-19, duration 1-60 minutes")
                except ValueError:
                    print("❌ Please enter valid numbers")
            elif choice == '3':
                await self.get_status()
            elif choice == '4':
                await self.stop_all()
            else:
                print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

def print_help():
    """Print help information"""
    print("""
🌱 Simple RainBird CLI - Help
============================

USAGE:
  python3 simple_cli.py [OPTIONS]

OPTIONS:
  --ip IP              Controller IP address (required for non-interactive)
  --password PASS      Controller password (required for non-interactive)
  --zone ZONE          Zone number to run (1-19)
  --duration MINS      Duration in minutes (1-60)
  --status             Get current irrigation status
  --stop               Stop all irrigation
  --help               Show this help

EXAMPLES:
  Interactive mode:
    python3 simple_cli.py

  Connect and run zone 1 for 10 minutes:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --zone 1 --duration 10

  Get status:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --status

  Stop all irrigation:
    python3 simple_cli.py --ip 192.168.1.113 --password 1234 --stop

FEATURES:
  ✅ Simple zone control
  ✅ Remaining time calculation
  ✅ Current status display
  ✅ Command-line parameters
  ✅ Interactive menu
  ✅ ESP-ME3 compatible
""")

async def main():
    parser = argparse.ArgumentParser(description='Simple RainBird Controller CLI', add_help=False)
    parser.add_argument('--ip', help='Controller IP address')
    parser.add_argument('--password', help='Controller password')
    parser.add_argument('--zone', type=int, help='Zone number (1-19)')
    parser.add_argument('--duration', type=int, help='Duration in minutes (1-60)')
    parser.add_argument('--status', action='store_true', help='Get current status')
    parser.add_argument('--stop', action='store_true', help='Stop all irrigation')
    parser.add_argument('--help', action='store_true', help='Show help')
    
    args = parser.parse_args()
    
    if args.help:
        print_help()
        return
    
    cli = SimpleRainBirdCLI(args.ip, args.password)
    
    try:
        # Command-line mode
        if args.ip and args.password:
            # Connect first
            if not await cli.connect():
                return
            
            # Execute requested action
            if args.zone and args.duration:
                if 1 <= args.zone <= 19 and 1 <= args.duration <= 60:
                    await cli.run_zone(args.zone, args.duration)
                else:
                    print("❌ Zone must be 1-19, duration 1-60 minutes")
            elif args.status:
                await cli.get_status()
            elif args.stop:
                await cli.stop_all()
            else:
                print("✅ Connected successfully")
        
        # Interactive mode
        else:
            await cli.interactive_menu()
    
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    finally:
        await cli.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
