# MCP Server - Live Demo Guide

## 🚀 Server Status

✅ **MCP Server is RUNNING on Port 8001**

```
http://127.0.0.1:8001
```

## 📡 Access Points

### 1. **REST API** (Direct HTTP calls)
```
GET    http://127.0.0.1:8001/api/account
GET    http://127.0.0.1:8001/api/dashboard
GET    http://127.0.0.1:8001/api/recommendations
POST   http://127.0.0.1:8001/api/chat
```

### 2. **MCP HTTP Protocol** (Standard MCP clients)
```
POST   http://127.0.0.1:8001/mcp
Headers:
  - Mcp-Session-Id: <session-id>
  - MCP-Protocol-Version: 2025-06-18
  - Content-Type: application/json
```

### 3. **Health Check**
```
GET    http://127.0.0.1:8001/health
```

---

## 🔧 Available MCP Tools

| # | Tool Name | Description |
|---|-----------|-------------|
| 1 | `get_account` | Get currently linked AWS account |
| 2 | `get_dashboard` | Get optimization dashboard with KPIs |
| 3 | `list_recommendations` | List optimization recommendations |
| 4 | `accept_recommendation` | Accept a recommendation |
| 5 | `reject_recommendation` | Reject a recommendation |
| 6 | `recur_recommendation` | Replay a recommendation |
| 7 | `list_events` | Get timeline events |
| 8 | `clear_events` | Clear event timeline |
| 9 | `get_observability` | Get observability metrics |
| 10 | `clear_observability` | Clear observability data |
| 11 | `get_chat_history` | Get chat conversation history |
| 12 | `clear_chat_history` | Clear chat history |
| 13 | `send_chat_message` | Send message to AI |
| 14 | `onboard_account` | Onboard AWS account (mocked or real) |
| 15 | `suggest_next_action` | Get next recommended action |

---

## 📝 Example: Call MCP Tool

### Using Python (requests)
```python
import requests
import json

BASE_URL = "http://127.0.0.1:8001"

# 1. Initialize session
init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "clientInfo": {"name": "my-client"}
    }
}
resp = requests.post(f"{BASE_URL}/mcp", json=init_payload)
session_id = resp.headers["Mcp-Session-Id"]

# 2. Send initialized notification
requests.post(
    f"{BASE_URL}/mcp",
    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    headers={
        "Mcp-Session-Id": session_id,
        "MCP-Protocol-Version": "2025-06-18"
    }
)

# 3. Call a tool
tool_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "get_account",
        "arguments": {}
    }
}

resp = requests.post(
    f"{BASE_URL}/mcp",
    json=tool_payload,
    headers={
        "Mcp-Session-Id": session_id,
        "MCP-Protocol-Version": "2025-06-18"
    }
)

result = resp.json()
print(json.dumps(result, indent=2))
```

### Using cURL
```bash
# 1. Initialize
curl -X POST http://127.0.0.1:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test"}}}'

# Get Mcp-Session-Id from response header, then use it for next calls

# 2. Call tool
curl -X POST http://127.0.0.1:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_account","arguments":{}}}'
```

---

## 🧪 Test Scripts

Run the demo scripts in `backend/`:

```powershell
# Test MCP HTTP protocol
python test_mcp_http.py

# Test with all tools
python test_mcp_tools.py

# Quick demo
python demo_mcp_server.py
```

---

## 🔌 Integration with AI Tools

### Claude Desktop
1. Edit `~/.claude_desktop_config.json`
2. Add this configuration:
```json
{
  "mcpServers": {
    "cloud-optimizer": {
      "command": "python",
      "args": ["-m", "app.mcp_stdio"],
      "cwd": "/path/to/backend"
    }
  }
}
```

### Cline (VS Code)
1. Open Cline settings
2. Add MCP Server:
   - Type: HTTP
   - URL: `http://127.0.0.1:8001/mcp`

---

## 📚 Resources

- **Backend Source**: `backend/app/mcp.py` - MCP protocol implementation
- **HTTP Transport**: `backend/app/main.py` - FastAPI with MCP endpoint
- **Stdio Transport**: `backend/app/mcp_stdio.py` - Process-based MCP server
- **Architecture Doc**: `VERCEL_DEPLOYMENT_ARCHITECTURE.md`

---

## 🌍 Deployed Endpoints

After Vercel deployment, the same MCP server is also available at:

```
https://cloud-optimizer-mcp-backend.vercel.app/mcp
https://cloud-optimizer-mcp-backend.vercel.app/api/...
```

---

## 💡 Tips

- **Session Management**: Each HTTP client needs a unique `Mcp-Session-Id`
- **Protocol Versioning**: Always include `MCP-Protocol-Version: 2025-06-18` header
- **Error Handling**: Check JSON-RPC error field for protocol errors
- **Reload**: Backend is running with `--reload` so code changes auto-refresh

---

**Status**: ✅ All systems operational  
**Port**: 8001  
**Protocol**: MCP 2.0 (JSON-RPC)  
**Transport**: HTTP (also available via stdio)
