#!/usr/bin/env python3
"""
Simple MCP Server Test
Tests the basic functionality of the Alpaca MCP server
"""

import json
import subprocess
import sys
from pathlib import Path

def test_mcp_server():
    """Test the MCP server with a simple account info request"""
    
    print("🚀 Testing Alpaca MCP Server...")
    print("=" * 40)
    
    # Paths
    server_dir = Path(__file__).parent / "alpaca-mcp-server"
    venv_python = server_dir / "venv" / "bin" / "python"
    server_script = server_dir / "alpaca_mcp_server.py"
    
    # Load API keys
    config_path = Path(__file__).parent / "analysts" / "config" / "api_keys.env"
    api_key = None
    secret_key = None
    
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                if line.startswith('ALPACA_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                elif line.startswith('ALPACA_SECRET_KEY='):
                    secret_key = line.split('=', 1)[1].strip()
    
    if not api_key or not secret_key:
        print("❌ API keys not found in config")
        return False
    
    # Environment
    env = {
        'ALPACA_API_KEY': api_key,
        'ALPACA_SECRET_KEY': secret_key,
        'ALPACA_PAPER_TRADE': 'True'
    }
    
    print(f"🔑 API Key: {api_key[:8]}...")
    print(f"📁 Server Path: {server_script}")
    print("")
    
    # Test 1: Check if server starts
    print("📡 Test 1: Server Startup")
    try:
        # Start server and send a simple request
        process = subprocess.Popen(
            [str(venv_python), str(server_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        request_data = json.dumps(init_request) + "\n"
        process.stdin.write(request_data)
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if 'result' in response:
                server_name = response['result'].get('serverInfo', {}).get('name', 'Unknown')
                print(f"✅ Server started successfully: {server_name}")
            else:
                print(f"❌ Server initialization failed: {response}")
                return False
        else:
            print("❌ No response from server")
            return False
        
        # Test 2: List available tools
        print("\n🔧 Test 2: Available Tools")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        request_data = json.dumps(tools_request) + "\n"
        process.stdin.write(request_data)
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if 'result' in response:
                tools = response['result'].get('tools', [])
                print(f"✅ Found {len(tools)} available tools")
                
                # Show some key tools
                key_tools = ['get_account_info', 'get_positions', 'place_stock_order', 'get_market_clock']
                for tool in tools:
                    if tool.get('name') in key_tools:
                        print(f"   ✓ {tool['name']}")
            else:
                print(f"❌ Failed to get tools: {response}")
                return False
        
        # Clean up
        process.stdin.close()
        process.terminate()
        process.wait()
        
        print("\n🎉 MCP Server test completed successfully!")
        print("\n📋 Next Steps:")
        print("   1. Configure Cursor with the MCP server (see MCP_INTEGRATION_GUIDE.md)")
        print("   2. Use natural language commands in Cursor")
        print("   3. Try the enhanced breakout scanner")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)

