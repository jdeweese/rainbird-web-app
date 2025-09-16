#!/usr/bin/env python3
"""
Simple connection test
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def test_connection():
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        print(f"🔌 Connecting to {config['controller_ip']}...")
        
        controller = async_client.CreateController(
            session,
            config['controller_ip'],
            config['controller_password']
        )
        
        # Test connection
        model_info = await controller.get_model_and_version()
        print(f"✅ Connected! Model: {model_info}")
        
        # Get zones
        print("🔍 Getting zones...")
        zones = await controller.get_available_stations()
        print(f"✅ Zones: {zones}")
        
        # Get status
        print("📊 Getting status...")
        irrigation_active = await controller.get_current_irrigation()
        print(f"✅ Irrigation active: {irrigation_active}")
        
        zone_states = await controller.get_zone_states()
        print(f"✅ Zone states: {zone_states}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(test_connection())
