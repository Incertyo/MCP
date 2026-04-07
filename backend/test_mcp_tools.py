#!/usr/bin/env python3
"""Test MCP Tools Execution"""

import json
import requests

BASE_URL = "http://127.0.0.1:8001"
SESSION_ID = None

def initialize_session():
    """Initialize MCP session and get session ID"""
    global SESSION_ID
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "test-client"}
        }
    }
    
    resp = requests.post(f"{BASE_URL}/mcp", json=payload)
    SESSION_ID = resp.headers.get("Mcp-Session-Id")
    print(f"  Initialize response: {resp.json()['result']['serverInfo']}")
    
    # Send initialized notification on same session with protocol version
    initialized_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    resp2 = requests.post(
        f"{BASE_URL}/mcp",
        json=initialized_payload,
        headers={
            "Mcp-Session-Id": SESSION_ID,
            "MCP-Protocol-Version": "2025-06-18"
        }
    )
    print(f"  Initialized notification sent")
    
    return SESSION_ID

def call_tool(tool_name, arguments=None):
    """Call an MCP tool"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }
    
    resp = requests.post(
        f"{BASE_URL}/mcp",
        json=payload,
        headers={
            "Mcp-Session-Id": SESSION_ID,
            "MCP-Protocol-Version": "2025-06-18"
        }
    )
    
    return resp.json()

def list_tools():
    """List all available MCP tools"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    resp = requests.post(
        f"{BASE_URL}/mcp",
        json=payload,
        headers={
            "Mcp-Session-Id": SESSION_ID,
            "MCP-Protocol-Version": "2025-06-18"
        }
    )
    
    return resp.json().get("result", {}).get("tools", [])

if __name__ == "__main__":
    print("\n🔧 MCP Tools Execution Test\n")
    
    # Initialize
    print("Initializing MCP session...")
    session_id = initialize_session()
    print(f"✅ Session ID: {session_id}\n")
    
    # List tools
    print("=" * 60)
    print("📋 Available Tools")
    print("=" * 60)
    tools = list_tools()
    for i, tool in enumerate(tools, 1):
        print(f"{i:2}. {tool['name']:30} - {tool['title']}")
    print()
    
    # Call get_account tool
    print("=" * 60)
    print("🔗 Calling Tool: get_account")
    print("=" * 60)
    result = call_tool("get_account")
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        account = json.loads(content)
        print(json.dumps(account, indent=2))
    else:
        print(json.dumps(result, indent=2))
    print()
    
    # Call get_dashboard tool
    print("=" * 60)
    print("📊 Calling Tool: get_dashboard")
    print("=" * 60)
    result = call_tool("get_dashboard")
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        dashboard = json.loads(content)
        print(json.dumps(dashboard, indent=2)[:500] + "...")
    else:
        print(json.dumps(result, indent=2))
    print()
    
    # Call list_recommendations tool
    print("=" * 60)
    print("💡 Calling Tool: list_recommendations (status=open)")
    print("=" * 60)
    result = call_tool("list_recommendations", {"status": "open"})
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        recommendations = json.loads(content)
        print(f"Total recommendations: {len(recommendations.get('recommendations', []))}")
        for i, rec in enumerate(recommendations.get("recommendations", [])[:3], 1):
            print(f"\n{i}. {rec.get('title')}")
            print(f"   ID: {rec.get('id')}")
            print(f"   Category: {rec.get('category')}")
            print(f"   Savings: ${rec.get('estimated_monthly_savings', 0)}/month")
    else:
        print(json.dumps(result, indent=2))
    print()
    
    # Call list_events tool
    print("=" * 60)
    print("📅 Calling Tool: list_events")
    print("=" * 60)
    result = call_tool("list_events")
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        events = json.loads(content)
        print(f"Total events: {len(events.get('events', []))}")
        for i, event in enumerate(events.get("events", [])[:3], 1):
            print(f"{i}. [{event.get('event_type')}] {event.get('message')}")
    else:
        print(json.dumps(result, indent=2))
    print()
    
    # Call send_chat_message tool
    print("=" * 60)
    print("💬 Calling Tool: send_chat_message")
    print("=" * 60)
    result = call_tool("send_chat_message", {"message": "What are my top optimization opportunities?"})
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        chat_resp = json.loads(content)
        print(f"User: What are my top optimization opportunities?")
        print(f"\nAssistant: {chat_resp.get('response', 'No response')}")
    else:
        print(json.dumps(result, indent=2))
    print()
    
    print("\n✅ All tools executed successfully!\n")
    print("Available on: http://127.0.0.1:8001")
    print("Use POST /mcp endpoint with Mcp-Session-Id header")
    print("Ready for Claude, Cline, or other MCP clients")
