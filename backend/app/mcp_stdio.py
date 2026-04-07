from __future__ import annotations

import json
import sys

from .domain_adapter import PrismDomainAdapter
from .mcp import McpConnectionState, PrismMcpServer
from .repository import build_repository
from .services import PrismService


def main() -> int:
    adapter = PrismDomainAdapter(PrismService(build_repository()))
    server = PrismMcpServer(adapter)
    state = McpConnectionState()

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue

        response = server.handle_payload(payload, state)
        if response is None:
            continue

        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
