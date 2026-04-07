import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import LocalJsonRepository
from app.config import settings


def build_client(tmp_path: Path) -> tuple[TestClient, LocalJsonRepository]:
    repository = LocalJsonRepository(tmp_path / "state.json")
    return TestClient(create_app(repository)), repository


def mocked_account_payload() -> dict[str, str]:
    return {
        "student_name": "Mohan",
        "email": "mohan@example.com",
        "aws_account_id": "123456789012",
        "connection_mode": "mocked",
        "access_key_id": "AKIA-STUDENT-DEMO",
        "secret_access_key": "demo-secret-placeholder",
        "session_token": "",
        "region": "ap-south-1",
        "institution": "AWS Student Lab",
    }


def auth_headers(session_id: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.mcp_api_key}",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
        headers["MCP-Protocol-Version"] = "2025-06-18"
    return headers


def initialize_session(client: TestClient) -> str:
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
            },
        },
        headers=auth_headers(),
    )
    assert response.status_code == 200
    session_id = response.headers["Mcp-Session-Id"]
    initialized = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=auth_headers(session_id),
    )
    assert initialized.status_code == 202
    return session_id


def test_mcp_initialize_and_advertise_capabilities(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "mcp_api_key", "test-key")
    client, _ = build_client(tmp_path)

    session_id = initialize_session(client)

    tools_response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=auth_headers(session_id))
    resources_response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "resources/list"}, headers=auth_headers(session_id))
    prompts_response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}, headers=auth_headers(session_id))

    assert tools_response.status_code == 200
    assert resources_response.status_code == 200
    assert prompts_response.status_code == 200
    assert any(tool["name"] == "get_dashboard" for tool in tools_response.json()["result"]["tools"])
    assert any(resource["uri"] == "prism://dashboard/current" for resource in resources_response.json()["result"]["resources"])
    assert any(prompt["name"] == "optimization-summary" for prompt in prompts_response.json()["result"]["prompts"])


def test_mcp_rejects_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "mcp_api_key", "test-key")
    client, _ = build_client(tmp_path)

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
            },
        },
    )

    assert response.status_code == 401


def test_mcp_tools_match_demo_state_and_block_recur_in_real_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "mcp_api_key", "test-key")
    client, repository = build_client(tmp_path)
    client.post("/api/account", json=mocked_account_payload())
    session_id = initialize_session(client)

    dashboard_response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "get_dashboard", "arguments": {}}},
        headers=auth_headers(session_id),
    )
    dashboard_payload = json.loads(dashboard_response.json()["result"]["content"][0]["text"])
    assert len(dashboard_payload["resources"]) == 4
    assert len(dashboard_payload["recommendations"]) == 3

    accept_response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "accept_recommendation", "arguments": {"recommendation_id": "rec-ec2-rightsize"}},
        },
        headers=auth_headers(session_id),
    )
    assert accept_response.json()["result"]["isError"] is False

    state = repository.load_state()
    assert state.account is not None
    state.account.connection_mode = "real"
    repository.save_state(state)

    recur_response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "recur_recommendation", "arguments": {"recommendation_id": "rec-ec2-rightsize"}},
        },
        headers=auth_headers(session_id),
    )
    assert recur_response.json()["result"]["isError"] is True
    assert "mocked aws mode" in recur_response.json()["result"]["content"][0]["text"].lower()


def test_agent_returns_grounded_next_action_without_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", True)
    client, _ = build_client(tmp_path)
    client.post("/api/account", json=mocked_account_payload())

    response = client.post("/api/agent/messages", json={"message": "What should I do next?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"] == []
    assert "next best action" in payload["answer"].lower()
    assert payload["snapshot"]["account"]["connection_mode"] == "mocked"


def test_agent_accepts_top_recommendation_with_single_safe_action(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", True)
    client, _ = build_client(tmp_path)
    client.post("/api/account", json=mocked_account_payload())

    response = client.post("/api/agent/messages", json={"message": "Accept the top recommendation"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["actions"]) == 1
    assert payload["actions"][0]["tool_name"] == "accept_recommendation"
    assert payload["actions"][0]["status"] == "executed"
    assert len([item for item in payload["snapshot"]["recommendations"] if item["status"] == "accepted"]) == 1


def test_agent_requests_onboarding_when_no_account_is_linked(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", True)
    client, _ = build_client(tmp_path)

    response = client.post("/api/agent/messages", json={"message": "What should I do next?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"] == []
    assert "account" in payload["answer"].lower()
    assert payload["snapshot"]["account"] is None


def test_stdio_mcp_exposes_same_capability_set(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "mcp_api_key", None)
    backend_dir = Path(__file__).resolve().parents[1]
    payload = "\n".join(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "stdio-test", "version": "1.0.0"},
                    },
                }
            ),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "resources/list"}),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}),
            "",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-m", "app.mcp_stdio"],
        input=payload,
        text=True,
        capture_output=True,
        cwd=backend_dir,
        check=True,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert any(tool["name"] == "get_dashboard" for tool in responses[1]["result"]["tools"])
    assert any(resource["uri"] == "prism://dashboard/current" for resource in responses[2]["result"]["resources"])
    assert any(prompt["name"] == "demo-walkthrough" for prompt in responses[3]["result"]["prompts"])
