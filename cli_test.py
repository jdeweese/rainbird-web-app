#!/usr/bin/env python3
"""
RainBird CLI Test Interface
Test PyRainBird library with controller
"""

import json
import asyncio
import sys
import aiohttp
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
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Create controller
            self.controller = async_client.CreateController(
                self.session,
                self.config['controller_ip'],
                self.config['controller_password']
            )
            
            # Test connection by getting model info
            model_info = await self.controller.get_model_and_version()
            print(f"✅ Connected successfully!")
            print(f"📋 Model: {model_info}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if self.session:
                await self.session.close()
            return False
    
    async def get_zones(self):
        """Get available zones"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("🔍 Getting available zones...")
            zones = await self.controller.get_available_stations()
            print(f"✅ Available zones: {zones}")
            return zones
        except Exception as e:
            print(f"❌ Failed to get zones: {e}")
    
    async def get_status(self):
        """Get current irrigation status"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("📊 Getting irrigation status...")
            status = await self.controller.get_current_irrigation()
            print(f"✅ Irrigation active: {status}")
            
            # Get zone states
            zone_states = await self.controller.get_zone_states()
            print(f"✅ Zone states: {zone_states}")
            return status
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
    
    async def start_zone(self, zone_id, duration_minutes):
        """Start irrigation for a zone"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print(f"🚿 Starting zone {zone_id} for {duration_minutes} minutes...")
            await self.controller.irrigate_zone(zone_id, duration_minutes)
            print(f"✅ Zone {zone_id} started successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to start zone: {e}")
    
    async def stop_irrigation(self):
        """Stop all irrigation"""
        if not self.controller:
            print("❌ Not connected to controller")
            return
        
        try:
            print("🛑 Stopping all irrigation...")
            await self.controller.stop_irrigation()
            print(f"✅ Irrigation stopped successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to stop irrigation: {e}")
    
    def show_menu(self):
        """Show CLI menu"""
        print("\n" + "="*50)
        print("🌱 RainBird Controller CLI")
        print("="*50)
        print("1. Connect to controller")
        print("2. Get available zones")
        print("3. Get irrigation status")
        print("4. Start zone")
        print("5. Stop all irrigation")
        print("6. Show config")
        print("0. Exit")
        print("="*50)
    
    def show_config(self):
        """Show current configuration"""
        print("\n📋 Current Configuration:")
        print(f"   IP: {self.config['controller_ip']}")
        print(f"   Password: {'*' * len(self.config['controller_password'])}")
        print(f"   Timeout: {self.config['timeout']}s")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def run(self):
        """Run CLI interface"""
        print("🌱 RainBird CLI Test Interface")
        print(f"📋 Controller: {self.config['controller_ip']}")
        
        try:
            while True:
                self.show_menu()
                choice = input("\nEnter choice: ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    await self.connect()
                elif choice == '2':
                    await self.get_zones()
                elif choice == '3':
                    await self.get_status()
                elif choice == '4':
                    zone_id = input("Enter zone ID: ").strip()
                    duration = input("Enter duration (minutes): ").strip()
                    try:
                        await self.start_zone(int(zone_id), int(duration))
                    except ValueError:
                        print("❌ Invalid zone ID or duration")
                elif choice == '5':
                    await self.stop_irrigation()
                elif choice == '6':
                    self.show_config()
                else:
                    print("❌ Invalid choice")
                
                input("\nPress Enter to continue...")
        finally:
            await self.cleanup()

async def main():
    """Main function"""
    cli = RainBirdCLI()
    await cli.run()

if __name__ == '__main__':
    asyncio.run(main())
