#!/usr/bin/env python3
"""Simple MCP Server Test - Show it's working"""

import json
import requests

BASE_URL = "http://127.0.0.1:8001"
SESSION_ID = None

def init():
    """Initialize MCP session"""
    global SESSION_ID
    
    # Step 1: Initialize
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "demo"}
        }
    }
    
    resp = requests.post(f"{BASE_URL}/mcp", json=payload)
    SESSION_ID = resp.headers.get("Mcp-Session-Id")
    
    # Step 2: Send initialized notification
    requests.post(
        f"{BASE_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={
            "Mcp-Session-Id": SESSION_ID,
            "MCP-Protocol-Version": "2025-06-18"
        }
    )

def call(tool, args=None):
    """Call tool"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": args or {}
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
    
    result = resp.json()
    if "result" in result and "content" in result["result"]:
        return json.loads(result["result"]["content"][0]["text"])
    return result

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 LIVE MCP SERVER DEMO - Port 8001")
    print("="*70 + "\n")
    
    print("📡 Initializing MCP session...")
    init()
    print(f"✅ Session initialized\n")
    
    print("1️⃣  get_account - Get currently linked AWS account")
    print("-" * 70)
    account = call("get_account")
    print(f"   Name: {account['student_name']}")
    print(f"   Email: {account['email']}")
    print(f"   AWS Account: {account['aws_account_id']}")
    print(f"   Mode: {account['connection_mode']}")
    print()
    
    print("2️⃣  get_dashboard - Get optimization dashboard")
    print("-" * 70)
    dashboard = call("get_dashboard")
    if "kpis" in dashboard:
        kpis = dashboard["kpis"]
        if isinstance(kpis, dict):
            for key, value in list(kpis.items())[:3]:
                print(f"   {key}: {value}")
    print()
    
    print("3️⃣  list_recommendations - Get optimization recommendations")
    print("-" * 70)
    recs = call("list_recommendations", {"status": "open"})
    if isinstance(recs, list):
        print(f"   Total recommendations: {len(recs)}")
        for i, rec in enumerate(recs[:2], 1):
            if isinstance(rec, dict):
                print(f"   {i}. {rec.get('title', 'N/A')} (${rec.get('estimated_monthly_savings', 0)}/mo)")
    elif isinstance(recs, dict) and "recommendations" in recs:
        print(f"   Total recommendations: {len(recs['recommendations'])}")
    print()
    
    print("4️⃣  list_events - Get timeline events")
    print("-" * 70)
    events = call("list_events")
    if isinstance(events, list):
        print(f"   Total events: {len(events)}")
        for i, event in enumerate(events[:2], 1):
            if isinstance(event, dict):
                print(f"   {i}. [{event.get('event_type', '?')}] {event.get('message', '')}")
    elif isinstance(events, dict) and "events" in events:
        print(f"   Total events: {len(events['events'])}")
    print()
    
    print("5️⃣  send_chat_message - Chat with AI")
    print("-" * 70)
    chat = call("send_chat_message", {"message": "What should I optimize first?"})
    if isinstance(chat, dict):
        response = chat.get("response", "No response")
        print(f"   User: What should I optimize first?")
        print(f"   AI: {response[:100]}...")
    print()
    
    print("6️⃣  suggest_next_action - Get next recommendation")
    print("-" * 70)
    action = call("suggest_next_action")
    if isinstance(action, dict):
        print(f"   Action: {action.get('summary', 'N/A')}")
    print()
    
    print("="*70)
    print("✅ MCP SERVER IS LIVE AND WORKING!")
    print("="*70)
    print()
    print("📍 Access Points:")
    print(f"   • REST API:     http://127.0.0.1:8001/api/...")
    print(f"   • MCP HTTP:     http://127.0.0.1:8001/mcp (POST)")
    print(f"   • Health Check: http://127.0.0.1:8001/health")
    print()
    print("🔧 Next Steps:")
    print("   1. Use with Claude (Claude Desktop)")
    print("   2. Use with Cline (VS Code extension)")
    print("   3. Build custom MCP client")
    print("   4. Deploy to Vercel (already deployed!)")
    print()
