"""
Fetches real metrics from Datadog API given a dashboard URL or service name.
Collects TPS, latency (p50/p95/p99), error rates, resource utilization.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone, timedelta
from typing import Any
import requests
from .config import settings


def _dd_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.dd_api_key:
        headers["DD-API-KEY"] = settings.dd_api_key
    if settings.dd_app_key:
        headers["DD-APPLICATION-KEY"] = settings.dd_app_key
    return headers


def _query_metric(query: str, from_ts: int, to_ts: int) -> list[float]:
    """Query a Datadog metric and return its values."""
    if not settings.dd_api_key:
        return []
    url = f"https://api.{settings.dd_site}/api/v1/query"
    params = {"query": query, "from": from_ts, "to": to_ts}
    try:
        resp = requests.get(url, params=params, headers=_dd_headers(), timeout=5)
        resp.raise_for_status()
        data = resp.json()
        series = data.get("series", [])
        if not series:
            return []
        points = series[0].get("pointlist", [])
        return [p[1] for p in points if p[1] is not None]
    except Exception:
        return []


def _extract_dashboard_id(dashboard_url: str) -> str | None:
    """Extract dashboard public ID from a Datadog URL."""
    match = re.search(r"dashboard/([a-zA-Z0-9-]+)", dashboard_url)
    return match.group(1) if match else None


def fetch_service_metrics(service_name: str, dashboard_url: str | None = None) -> dict[str, Any]:
    """
    Fetch TPS, latency (p50/p95/p99), and error rate for a service.
    Returns mocked data when Datadog API is not configured.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    one_hour_ago = now - 3600

    if not settings.dd_api_key:
        # Return realistic mock data when Datadog is not configured
        return {
            "tps": {"average": 45.2, "peak": 312.7},
            "latency_ms": {"p50": 12.4, "p95": 89.3, "p99": 245.6},
            "error_rate_percent": 0.34,
            "data_source": "mocked",
            "service": service_name,
        }

    tag = f"service:{service_name}"

    tps_values = _query_metric(f"sum:trace.web.request.hits{{{tag}}}.as_rate()", one_hour_ago, now)
    p50_values = _query_metric(f"p50:trace.web.request.duration{{{tag}}}", one_hour_ago, now)
    p95_values = _query_metric(f"p95:trace.web.request.duration{{{tag}}}", one_hour_ago, now)
    p99_values = _query_metric(f"p99:trace.web.request.duration{{{tag}}}", one_hour_ago, now)
    err_values = _query_metric(f"sum:trace.web.request.errors{{{tag}}}.as_rate()", one_hour_ago, now)

    def avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    def peak(lst: list[float]) -> float:
        return round(max(lst), 2) if lst else 0.0

    return {
        "tps": {"average": avg(tps_values), "peak": peak(tps_values)},
        "latency_ms": {
            "p50": avg(p50_values) * 1000,
            "p95": avg(p95_values) * 1000,
            "p99": avg(p99_values) * 1000,
        },
        "error_rate_percent": round(avg(err_values) * 100, 3),
        "data_source": "datadog_live",
        "service": service_name,
    }


def fetch_aws_service_utilization(service_name: str, aws_service: str) -> dict[str, Any]:
    """Fetch utilization metrics for a specific AWS service."""
    if not settings.dd_api_key:
        utilization_mock = {
            "DynamoDB": {"read_capacity_used": 62.3, "write_capacity_used": 28.1, "throttled_requests": 0.02},
            "S3": {"get_requests_per_min": 1240.0, "put_requests_per_min": 89.0, "data_transfer_gb": 12.4},
            "Lambda": {"invocations_per_min": 450.0, "error_rate": 0.5, "avg_duration_ms": 320.0},
            "RDS": {"cpu_percent": 42.0, "connections": 18.0, "read_iops": 420.0, "write_iops": 88.0},
        }
        return utilization_mock.get(aws_service, {"utilization": 0.0})
    return {}