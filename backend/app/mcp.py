from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Any

from .domain_adapter import PrismDomainAdapter
from .models import AccountInput

# Import new modules for extended tools
try:
    from .codebase_analyzer_v2 import CodebaseAnalyzer, get_mock_codebase_analysis
    from .observability_client import ObservabilityClient, get_mock_metrics
    from .cost_aggregator_v2 import CostAggregator, get_mock_costs
    from .aws_service_knowledge import get_service_info, compare_services, estimate_cost
    from .schema import build_unified_report, validate_schema
    NEW_TOOLS_AVAILABLE = True
except ImportError:
    NEW_TOOLS_AVAILABLE = False

JSONRPC_VERSION = "2.0"
LATEST_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


class McpProtocolError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class McpHttpError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class McpConnectionState:
    protocol_version: str | None = None
    initialize_seen: bool = False
    initialized: bool = False
    client_info: dict[str, Any] | None = None


class PrismMcpServer:
    def __init__(self, adapter: PrismDomainAdapter) -> None:
        self.adapter = adapter
        self._http_sessions: dict[str, McpConnectionState] = {}

    def create_http_session(self) -> tuple[str, McpConnectionState]:
        session_id = secrets.token_urlsafe(24)
        state = McpConnectionState()
        self._http_sessions[session_id] = state
        return session_id, state

    def get_http_session(self, session_id: str) -> McpConnectionState | None:
        return self._http_sessions.get(session_id)

    def delete_http_session(self, session_id: str) -> bool:
        return self._http_sessions.pop(session_id, None) is not None

    def ensure_http_state(self, payload: Any, session_id: str | None) -> tuple[McpConnectionState, str | None]:
        if session_id:
            state = self.get_http_session(session_id)
            if state is None:
                raise McpHttpError(404, "Unknown MCP session.")
            return state, None

        if not self._is_initialize_payload(payload):
            raise McpHttpError(400, "Missing Mcp-Session-Id header for non-initialize MCP request.")

        new_session_id, state = self.create_http_session()
        return state, new_session_id

    def handle_payload(self, payload: Any, state: McpConnectionState) -> Any | None:
        if isinstance(payload, list):
            responses: list[dict[str, Any]] = []
            for item in payload:
                response = self._handle_message(item, state)
                if response is not None:
                    responses.append(response)
            return responses or None

        return self._handle_message(payload, state)

    def _handle_message(self, message: Any, state: McpConnectionState) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return self._error_response(None, -32600, "Invalid Request")

        request_id = message.get("id")
        method = message.get("method")

        if method is None:
            return None

        try:
            result = self._dispatch(method, message.get("params") or {}, state)
        except McpProtocolError as exc:
            if request_id is None:
                return None
            return self._error_response(request_id, exc.code, exc.message, exc.data)

        if request_id is None:
            return None
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _dispatch(self, method: str, params: dict[str, Any], state: McpConnectionState) -> dict[str, Any]:
        if method == "initialize":
            return self._initialize(params, state)
        if method == "notifications/initialized":
            state.initialized = True
            return {}
        if method == "ping":
            return {}

        if not state.initialize_seen:
            raise McpProtocolError(-32002, "Server not initialized")
        if not state.initialized:
            raise McpProtocolError(-32002, "Client has not completed the initialized notification.")

        if method == "tools/list":
            return {"tools": self._tool_definitions()}
        if method == "tools/call":
            return self._call_tool(params)
        if method == "resources/list":
            return {"resources": self._resources()}
        if method == "resources/templates/list":
            return {"resourceTemplates": self._resource_templates()}
        if method == "resources/read":
            return self._read_resource(params)
        if method == "prompts/list":
            return {"prompts": self._prompts()}
        if method == "prompts/get":
            return self._get_prompt(params)

        if method.startswith("notifications/"):
            return {}

        raise McpProtocolError(-32601, f"Method not found: {method}")

    def _initialize(self, params: dict[str, Any], state: McpConnectionState) -> dict[str, Any]:
        requested_version = params.get("protocolVersion")
        if not isinstance(requested_version, str):
            raise McpProtocolError(-32602, "protocolVersion must be provided.")

        protocol_version = requested_version if requested_version in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        state.protocol_version = protocol_version
        state.client_info = params.get("clientInfo") if isinstance(params.get("clientInfo"), dict) else None
        state.initialize_seen = True
        state.initialized = False
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "prompts": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "cloud-optimizer-prism",
                "title": "Cloud Optimizer Prism MCP",
                "version": "0.2.0",
            },
            "instructions": "Use Prism tools for seeded cloud optimization workflows. Live AWS mutations are not supported.",
        }

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            raise McpProtocolError(-32602, "Tool name must be provided.")
        if not isinstance(arguments, dict):
            raise McpProtocolError(-32602, "Tool arguments must be an object.")

        try:
            payload = self._execute_tool(name, arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, indent=2),
                    }
                ],
                "isError": False,
            }
        except Exception as exc:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(exc),
                    }
                ],
                "isError": True,
            }

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "get_account":
            return self.adapter.to_python(self.adapter.get_account())
        if name == "get_dashboard":
            return self.adapter.to_python(self.adapter.get_dashboard())
        if name == "list_recommendations":
            status = arguments.get("status")
            return self.adapter.to_python(self.adapter.list_recommendations(status=status))
        if name == "accept_recommendation":
            return self.adapter.to_python(self.adapter.accept_recommendation(self._required_string(arguments, "recommendation_id")))
        if name == "reject_recommendation":
            return self.adapter.to_python(self.adapter.reject_recommendation(self._required_string(arguments, "recommendation_id")))
        if name == "recur_recommendation":
            return self.adapter.to_python(self.adapter.recur_recommendation(self._required_string(arguments, "recommendation_id")))
        if name == "list_events":
            return self.adapter.to_python(self.adapter.list_events())
        if name == "clear_events":
            return self.adapter.to_python(self.adapter.clear_events())
        if name == "get_observability":
            return self.adapter.to_python(self.adapter.get_observability())
        if name == "clear_observability":
            return self.adapter.to_python(self.adapter.clear_observability())
        if name == "get_chat_history":
            return self.adapter.to_python(self.adapter.get_chat_history())
        if name == "clear_chat_history":
            return self.adapter.to_python(self.adapter.clear_chat_history())
        if name == "send_chat_message":
            return self.adapter.to_python(self.adapter.send_chat_message(self._required_string(arguments, "message")))
        if name == "onboard_account":
            return self.adapter.to_python(self.adapter.onboard_account(AccountInput.model_validate(arguments)))
        if name == "suggest_next_action":
            return self.adapter.to_python(self.adapter.suggest_next_action())
        if name == "get_aws_service_usage_pattern_data":
            return self.adapter.to_python(self.adapter.get_aws_service_usage_pattern_data(
                service_name=self._required_string(arguments, "service_name"),
                aws_service_name=arguments.get("aws_service_name"),
            ))
        if name == "analyze_codebase":
            return self.adapter.to_python(self.adapter.analyze_codebase(
                service_name=self._required_string(arguments, "service_name"),
                files=arguments.get("files", []),
            ))
        if name == "get_datadog_metrics":
            return self.adapter.to_python(self.adapter.get_datadog_metrics(
                service_name=self._required_string(arguments, "service_name"),
                dashboard_url=arguments.get("dashboard_url"),
            ))
        if name == "get_aws_service_costs":
            return self.adapter.to_python(self.adapter.get_aws_service_costs(
                service_name=self._required_string(arguments, "service_name"),
                aws_services=arguments.get("aws_services", []),
            ))
        if name == "get_aws_service_info":
            return self.adapter.to_python(self.adapter.get_aws_service_info(
                aws_service_name=self._required_string(arguments, "aws_service_name"),
            ))
        if name == "generate_cost_optimization_report":
            return self.adapter.to_python(self.adapter.generate_cost_optimization_report(
                service_name=self._required_string(arguments, "service_name"),
                files=arguments.get("files", []),
                datadog_dashboard_url=arguments.get("datadog_dashboard_url"),
            ))

        # New extended tools
        if not NEW_TOOLS_AVAILABLE:
            raise McpProtocolError(-32601, f"Tool not available: {name}")

        if name == "extract_codebase_services":
            repo_path = arguments.get("repo_path", ".")
            try:
                analyzer = CodebaseAnalyzer(repo_path)
                result = analyzer.scan()
                result["fallback"] = False
                return result
            except Exception:
                result = get_mock_codebase_analysis()
                result["fallback"] = True
                return result

        if name == "get_observability_metrics":
            service_name = self._required_string(arguments, "service_name")
            time_range_hours = arguments.get("time_range_hours", 720)
            try:
                import os
                client = ObservabilityClient(
                    datadog_api_key=os.environ.get("DD_API_KEY"),
                    datadog_app_key=os.environ.get("DD_APP_KEY"),
                )
                result = client.get_service_metrics(service_name, time_range_hours)
                result["fallback"] = False
                return result
            except Exception:
                result = get_mock_metrics(service_name)
                result["fallback"] = True
                return result

        if name == "get_cost_breakdown":
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            try:
                aggregator = CostAggregator()
                result = aggregator.get_monthly_costs(start_date, end_date)
                result["fallback"] = False
                return result
            except Exception:
                result = get_mock_costs()
                result["fallback"] = True
                return result

        if name == "get_aws_service_info_v2":
            service_name = self._required_string(arguments, "service_name")
            return get_service_info(service_name)

        if name == "compare_aws_services":
            use_case = self._required_string(arguments, "use_case")
            return compare_services(use_case)

        if name == "get_unified_report":
            repo_path = arguments.get("repo_path", ".")
            time_range_hours = arguments.get("time_range_hours", 720)
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")

            # 1. Get codebase analysis
            try:
                analyzer = CodebaseAnalyzer(repo_path)
                codebase = analyzer.scan()
            except Exception:
                codebase = get_mock_codebase_analysis()

            # 2. Get metrics for each service in codebase
            services = list(codebase.get("service_summary", {}).keys())
            metrics = {}
            for service in services:
                try:
                    client = ObservabilityClient()
                    metrics[service] = client.get_service_metrics(service, time_range_hours)
                except Exception:
                    metrics[service] = get_mock_metrics(service)

            # 3. Get cost breakdown
            try:
                aggregator = CostAggregator()
                costs = aggregator.get_monthly_costs(start_date, end_date)
            except Exception:
                costs = get_mock_costs()

            # 4. Get AWS service info for each service
            aws_info = {}
            for service in services:
                info = get_service_info(service)
                if "not_found" not in info:
                    aws_info[service] = info

            # 5. Build unified report
            report = build_unified_report(codebase, metrics, costs, aws_info)
            report["fallback"] = False

            # 6. Save to file
            try:
                with open("unified_report.json", "w") as f:
                    json.dump(report, f, indent=2, default=str)
            except Exception:
                pass

            return report

        raise McpProtocolError(-32601, f"Unknown tool: {name}")

    def _read_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri")
        if not isinstance(uri, str):
            raise McpProtocolError(-32602, "Resource URI must be provided.")
        content = self._resource_contents(uri)
        return {"contents": [content]}

    def _resource_contents(self, uri: str) -> dict[str, Any]:
        if uri == "prism://account/current":
            data = self.adapter.to_python(self.adapter.get_account())
        elif uri == "prism://dashboard/current":
            data = self.adapter.to_python(self.adapter.get_dashboard())
        elif uri == "prism://recommendations/open":
            data = self.adapter.to_python(self.adapter.list_recommendations(status="open"))
        elif uri == "prism://recommendations/all":
            data = self.adapter.to_python(self.adapter.list_recommendations())
        elif uri == "prism://events/recent":
            data = self.adapter.to_python(self.adapter.list_events())
        elif uri == "prism://observability/summary":
            data = self.adapter.to_python(self.adapter.get_observability())
        elif uri.startswith("prism://recommendations/"):
            recommendation_id = uri.rsplit("/", 1)[-1]
            data = self.adapter.to_python(self.adapter.get_recommendation(recommendation_id))
        else:
            raise McpProtocolError(-32602, f"Unknown resource URI: {uri}")

        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(data, indent=2),
        }

    def _get_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            raise McpProtocolError(-32602, "Prompt name must be provided.")
        if not isinstance(arguments, dict):
            raise McpProtocolError(-32602, "Prompt arguments must be an object.")

        prompt = self._prompt_by_name(name)
        return {
            "description": prompt["description"],
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt["builder"](arguments),
                    },
                }
            ],
        }

    def _tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {"name": "get_account", "title": "Get Account", "description": "Return the currently linked AWS account profile.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "get_dashboard", "title": "Get Dashboard", "description": "Return the current seeded dashboard state.", "inputSchema": {"type": "object", "properties": {}}},
            {
                "name": "list_recommendations",
                "title": "List Recommendations",
                "description": "List current optimization recommendations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "enum": ["open", "accepted", "rejected"]}},
                },
            },
            {
                "name": "accept_recommendation",
                "title": "Accept Recommendation",
                "description": "Accept a seeded optimization recommendation.",
                "inputSchema": {"type": "object", "properties": {"recommendation_id": {"type": "string"}}, "required": ["recommendation_id"]},
            },
            {
                "name": "reject_recommendation",
                "title": "Reject Recommendation",
                "description": "Reject a seeded optimization recommendation.",
                "inputSchema": {"type": "object", "properties": {"recommendation_id": {"type": "string"}}, "required": ["recommendation_id"]},
            },
            {
                "name": "recur_recommendation",
                "title": "Replay Recommendation",
                "description": "Replay a seeded recommendation in mocked mode.",
                "inputSchema": {"type": "object", "properties": {"recommendation_id": {"type": "string"}}, "required": ["recommendation_id"]},
            },
            {"name": "list_events", "title": "List Events", "description": "List recent Prism timeline events.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "clear_events", "title": "Clear Events", "description": "Clear the event timeline.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "get_observability", "title": "Get Observability", "description": "Return observability metrics and recent events.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "clear_observability", "title": "Clear Observability", "description": "Clear observability counters and signals.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "get_chat_history", "title": "Get Chat History", "description": "Return the existing chat history.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "clear_chat_history", "title": "Clear Chat History", "description": "Clear the existing chat history.", "inputSchema": {"type": "object", "properties": {}}},
            {
                "name": "send_chat_message",
                "title": "Send Chat Message",
                "description": "Send a user message through the existing chat flow.",
                "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            },
            {
                "name": "onboard_account",
                "title": "Onboard Account",
                "description": "Link a mocked or real AWS account using the existing onboarding flow.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "student_name": {"type": "string"},
                        "email": {"type": "string"},
                        "aws_account_id": {"type": "string"},
                        "connection_mode": {"type": "string", "enum": ["mocked", "real"]},
                        "access_key_id": {"type": "string"},
                        "secret_access_key": {"type": "string"},
                        "session_token": {"type": "string"},
                        "region": {"type": "string"},
                        "institution": {"type": "string"},
                    },
                    "required": ["student_name", "email", "aws_account_id", "connection_mode", "access_key_id", "secret_access_key", "session_token", "region", "institution"],
                },
            },
            {"name": "suggest_next_action", "title": "Suggest Next Action", "description": "Summarize the next best recommendation to apply.", "inputSchema": {"type": "object", "properties": {}}},
            {
                "name": "get_aws_service_usage_pattern_data",
                "title": "Get AWS Service Usage Pattern Data",
                "description": "Returns service usage pattern details, Datadog metrics, and monthly cost breakdown for all AWS services used in a microservice codebase.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Name of the microservice"},
                        "aws_service_name": {"type": "string", "description": "Optionally filter by specific AWS service"},
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "analyze_codebase",
                "title": "Analyze Codebase",
                "description": "Parse IaC and business logic files to identify which AWS services are used and how (read/write patterns, resource names, code references).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "content": {"type": "string"},
                                    "file_type": {"type": "string", "enum": ["iac", "business_logic"]},
                                },
                            },
                        },
                    },
                    "required": ["service_name", "files"],
                },
            },
            {
                "name": "get_datadog_metrics",
                "title": "Get Datadog Metrics",
                "description": "Fetch TPS, latency (p50/p95/p99), and error rate metrics for a service from Datadog.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "dashboard_url": {"type": "string", "description": "Optional Datadog dashboard URL"},
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "get_aws_service_costs",
                "title": "Get AWS Service Costs",
                "description": "Retrieve monthly cost data for AWS services used by a microservice, normalized by read/write/storage operation types.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "aws_services": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["service_name", "aws_services"],
                },
            },
            {
                "name": "get_aws_service_info",
                "title": "Get AWS Service Info",
                "description": "Get AWS service knowledge: when to use it, cost model, optimization tips, and alternatives. Helps LLM reason about cloud service selection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "aws_service_name": {"type": "string", "enum": ["DynamoDB", "S3", "Lambda", "RDS", "APIGateway", "SQS", "SNS", "ElastiCache"]},
                    },
                    "required": ["aws_service_name"],
                },
            },
            {
                "name": "generate_cost_optimization_report",
                "title": "Generate Cost Optimization Report",
                "description": "Orchestrates codebase analysis, metrics collection, cost aggregation, and LLM reasoning to produce a full cost optimization report.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "files": {"type": "array", "items": {"type": "object"}},
                        "datadog_dashboard_url": {"type": "string"},
                    },
                    "required": ["service_name", "files"],
                },
            },
            # New extended tools
            {
                "name": "extract_codebase_services",
                "title": "Extract Codebase Services",
                "description": "Scan a repository to detect AWS cloud service usage from IaC (Terraform/CloudFormation) and business logic (boto3/CDK).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the repository to scan", "default": "."},
                    },
                },
            },
            {
                "name": "get_observability_metrics",
                "title": "Get Observability Metrics",
                "description": "Fetch TPS, latency (p50/p95/p99), error rate, and resource utilization metrics for a service from Datadog or CloudWatch.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Name of the service"},
                        "time_range_hours": {"type": "integer", "description": "Time range in hours", "default": 720},
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "get_cost_breakdown",
                "title": "Get Cost Breakdown",
                "description": "Retrieve monthly AWS cost data normalized by service and operation type (read/write/storage/transfer).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                        "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    },
                },
            },
            {
                "name": "get_aws_service_info_v2",
                "title": "Get AWS Service Info (Extended)",
                "description": "Get detailed AWS service knowledge including when to use, cost model, optimization tips, and alternatives.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "AWS service name (e.g., s3, dynamodb, lambda)"},
                    },
                    "required": ["service_name"],
                },
            },
            {
                "name": "compare_aws_services",
                "title": "Compare AWS Services",
                "description": "Find the best AWS services for a given use case by matching against service capabilities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "use_case": {"type": "string", "description": "Natural language description of the use case"},
                    },
                    "required": ["use_case"],
                },
            },
            {
                "name": "get_unified_report",
                "title": "Get Unified Report",
                "description": "Generate a comprehensive unified report combining codebase analysis, observability metrics, cost data, and AWS service insights.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the repository to analyze", "default": "."},
                        "time_range_hours": {"type": "integer", "description": "Time range for metrics in hours", "default": 720},
                        "start_date": {"type": "string", "description": "Start date for cost data in YYYY-MM-DD format"},
                        "end_date": {"type": "string", "description": "End date for cost data in YYYY-MM-DD format"},
                    },
                },
            },
        ]

    def _resources(self) -> list[dict[str, Any]]:
        return [
            {"uri": "prism://account/current", "name": "Current account", "title": "Current linked account", "description": "The active AWS account profile.", "mimeType": "application/json"},
            {"uri": "prism://dashboard/current", "name": "Current dashboard", "title": "Current dashboard snapshot", "description": "The live dashboard state for the demo environment.", "mimeType": "application/json"},
            {"uri": "prism://recommendations/open", "name": "Open recommendations", "title": "Open recommendations", "description": "All currently open optimization recommendations.", "mimeType": "application/json"},
            {"uri": "prism://recommendations/all", "name": "All recommendations", "title": "All recommendations", "description": "All recommendations regardless of status.", "mimeType": "application/json"},
            {"uri": "prism://events/recent", "name": "Recent events", "title": "Recent Prism events", "description": "Timeline events generated by Prism.", "mimeType": "application/json"},
            {"uri": "prism://observability/summary", "name": "Observability summary", "title": "Observability summary", "description": "Telemetry summary and recent observability events.", "mimeType": "application/json"},
        ]

    def _resource_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "uriTemplate": "prism://recommendations/{id}",
                "name": "Recommendation by id",
                "title": "Recommendation details",
                "description": "Read a single recommendation by its identifier.",
                "mimeType": "application/json",
            }
        ]

    def _prompts(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "optimization-summary",
                "title": "Optimization Summary",
                "description": "Summarize the current optimization posture for the linked account.",
            },
            {
                "name": "recommendation-review",
                "title": "Recommendation Review",
                "description": "Review a recommendation before accepting or rejecting it.",
                "arguments": [{"name": "recommendation_id", "description": "The recommendation to inspect.", "required": False}],
            },
            {
                "name": "account-onboarding-guide",
                "title": "Account Onboarding Guide",
                "description": "Guide a user through mocked or real AWS account onboarding.",
            },
            {
                "name": "demo-walkthrough",
                "title": "Demo Walkthrough",
                "description": "Walk a user through the full Cloud Optimizer demo flow.",
            },
        ]

    def _prompt_by_name(self, name: str) -> dict[str, Any]:
        next_action = self.adapter.suggest_next_action()
        prompts: dict[str, dict[str, Any]] = {
            "optimization-summary": {
                "description": "Summarize the current optimization posture for the linked account.",
                "builder": lambda _arguments: (
                    "Summarize the linked Prism account, current KPIs, open recommendations, and the most important risk or savings opportunity."
                ),
            },
            "recommendation-review": {
                "description": "Review a recommendation before accepting or rejecting it.",
                "builder": lambda arguments: (
                    f"Review recommendation {arguments.get('recommendation_id', 'the top open recommendation')} and explain the tradeoffs, projected savings, and operational impact."
                ),
            },
            "account-onboarding-guide": {
                "description": "Guide a user through mocked or real AWS account onboarding.",
                "builder": lambda _arguments: (
                    "Explain how to onboard a mocked demo account versus a real AWS account, including when each mode is appropriate and what data is seeded afterward."
                ),
            },
            "demo-walkthrough": {
                "description": "Walk a user through the full Cloud Optimizer demo flow.",
                "builder": lambda _arguments: (
                    "Walk through the Cloud Optimizer demo from account onboarding to dashboard review, recommendation action, chat usage, and observability. "
                    f"Current next best action: {next_action['summary']}"
                ),
            },
        }
        if name not in prompts:
            raise McpProtocolError(-32602, f"Unknown prompt: {name}")
        return prompts[name]

    def _is_initialize_payload(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            return payload.get("method") == "initialize"
        if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
            return payload[0].get("method") == "initialize"
        return False

    @staticmethod
    def _required_string(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value:
            raise McpProtocolError(-32602, f"{key} must be a non-empty string.")
        return value

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error}
