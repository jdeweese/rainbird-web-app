#!/usr/bin/env python3
"""
Test RPC methods for program data - this might be what your apps use
"""

import asyncio
import aiohttp
import json
from pyrainbird import async_client

async def test_rpc_programs():
    print("🔍 TESTING RPC METHODS FOR PROGRAM DATA")
    print("="*50)
    print("💡 This might be how your apps get program info")
    print("="*50)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    session = aiohttp.ClientSession()
    
    try:
        controller = async_client.CreateController(
            session, config['controller_ip'], config['controller_password']
        )
        
        # Test all possible RPC methods
        rpc_methods = [
            'getProgramInfo', 'getSettings', 'getPrograms', 'getSchedule',
            'getProgramA', 'getProgramB', 'getProgramC', 'getProgramD',
            'getProgram1', 'getProgram2', 'getProgram3', 'getProgram4',
            'getAllPrograms', 'getProgramData', 'getScheduleData'
        ]
        
        print("🧪 Testing all possible RPC methods:")
        for method in rpc_methods:
            try:
                result = await controller.test_rpc_support(method)
                print(f"✅ {method}: {result}")
            except Exception as e:
                print(f"❌ {method}: {str(e)[:50]}...")
        
        print(f"\n🎯 SUCCESSFUL RPC CALLS:")
        print("-" * 30)
        
        # Get the working ones in detail
        try:
            program_info = await controller.test_rpc_support('getProgramInfo')
            print(f"📋 getProgramInfo: {json.dumps(program_info, indent=2)}")
        except:
            pass
        
        try:
            settings = await controller.test_rpc_support('getSettings')
            print(f"⚙️  getSettings: {json.dumps(settings, indent=2)}")
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(test_rpc_programs())
