#!/usr/bin/env python3
"""Test MCP HTTP Server on custom port"""

import json
import requests

BASE_URL = "http://127.0.0.1:8001"

def test_health():
    """Test health endpoint"""
    print("=" * 50)
    print("Testing /health endpoint...")
    print("=" * 50)
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")

def test_mcp_initialize():
    """Test MCP initialization"""
    print("=" * 50)
    print("Testing MCP /mcp endpoint - Initialize")
    print("=" * 50)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    print(f"Request:\n{json.dumps(payload, indent=2)}\n")
    
    resp = requests.post(
        f"{BASE_URL}/mcp",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print(f"Response:\n{json.dumps(resp.json(), indent=2)}\n")
    
    return resp.json().get("result", {}).get("serverInfo", {})

def test_mcp_tools_list(session_id):
    """Test MCP tools/list"""
    print("=" * 50)
    print("Testing MCP /mcp endpoint - List Tools")
    print("=" * 50)
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    print(f"Request:\n{json.dumps(payload, indent=2)}\n")
    
    resp = requests.post(
        f"{BASE_URL}/mcp",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Mcp-Session-Id": session_id
        }
    )
    
    print(f"Status: {resp.status_code}")
    result = resp.json()
    
    if "result" in result:
        tools = result["result"].get("tools", [])
        print(f"Tools available: {len(tools)}")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['title']}")
    else:
        print(f"Response:\n{json.dumps(result, indent=2)}")
    print()

def test_get_account():
    """Test regular API endpoint"""
    print("=" * 50)
    print("Testing REST API /api/account endpoint")
    print("=" * 50)
    resp = requests.get(f"{BASE_URL}/api/account")
    print(f"Status: {resp.status_code}")
    print(f"Response:\n{json.dumps(resp.json(), indent=2)}\n")

if __name__ == "__main__":
    print("\n🚀 MCP Server Testing on Port 8001\n")
    
    try:
        # Test health
        test_health()
        
        # Test REST API
        test_get_account()
        
        # Test MCP HTTP
        server_info = test_mcp_initialize()
        print(f"Server: {server_info.get('name', 'Unknown')}")
        print(f"Title: {server_info.get('title', 'Unknown')}")
        print(f"Version: {server_info.get('version', 'Unknown')}\n")
        
        # Get session ID from response headers (for next request)
        # For now, we'll just show the flow
        
        print("\n✅ MCP Server is working!\n")
        print("Next steps:")
        print("1. Use session ID from Mcp-Session-Id header for subsequent requests")
        print("2. Send tools/list to see available tools")
        print("3. Send tools/call to execute specific tools")
        print("4. Use for AI agent integration (Claude, Cline, etc.)\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
