"""
Generates a structured Cost Optimization Report by orchestrating:
- Codebase analysis
- Datadog metrics
- AWS cost aggregation
- AWS knowledge base
- LLM reasoning
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .codebase_analyzer import analyze_codebase, AwsServiceUsage
from .metrics_fetcher import fetch_service_metrics, fetch_aws_service_utilization
from .cost_aggregator import aggregate_costs
from .aws_knowledge import get_service_info, get_optimization_tips
from .llm import gemini_client


def build_usage_pattern_data(
    service_name: str,
    files: list[dict],
    datadog_dashboard_url: str | None = None,
) -> dict[str, Any]:
    """Build the unified JSON schema output per Slide 3 of the PPTX."""
    usages: list[AwsServiceUsage] = analyze_codebase(files)
    aws_service_names = [u.name for u in usages]

    metrics = fetch_service_metrics(service_name, datadog_dashboard_url)
    costs = aggregate_costs(service_name, aws_service_names)

    aws_services_out = []
    for usage in usages:
        aws_services_out.append({
            "name": usage.name,
            "operations_detected": usage.operations_detected,
            "tables": usage.tables,
            "buckets": usage.buckets,
            "throughput_mode": usage.throughput_mode,
            "code_references": usage.code_references[:10],  # limit for JSON size
            "read_operations": usage.read_operations,
            "write_operations": usage.write_operations,
        })

    monthly_cost_usd = {}
    for svc, cost in costs.items():
        monthly_cost_usd[svc] = cost["total"]
    monthly_cost_usd["total"] = round(sum(monthly_cost_usd.values()), 2)

    return {
        "service_name": service_name,
        "aws_services": aws_services_out,
        "metrics": {
            "tps": metrics["tps"],
            "latency_ms": metrics["latency_ms"],
            "error_rate_percent": metrics["error_rate_percent"],
        },
        "monthly_cost_usd": monthly_cost_usd,
        "cost_breakdown": costs,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_cost_optimization_report(
    service_name: str,
    usage_pattern_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate a full cost optimization report from usage pattern data + LLM reasoning."""
    aws_services = [s["name"] for s in usage_pattern_data.get("aws_services", [])]
    total_cost = usage_pattern_data.get("monthly_cost_usd", {}).get("total", 0.0)
    metrics = usage_pattern_data.get("metrics", {})

    # Gather findings and tips from knowledge base
    findings = []
    recommendations = []
    estimated_savings = 0.0

    for svc_data in usage_pattern_data.get("aws_services", []):
        svc_name = svc_data["name"]
        kb = get_service_info(svc_name)
        tips = get_optimization_tips(svc_name)
        svc_cost = usage_pattern_data.get("cost_breakdown", {}).get(svc_name, {})
        monthly = svc_cost.get("total", 0.0)

        # Generate findings
        finding = {
            "service": svc_name,
            "monthly_cost": monthly,
            "operations_detected": svc_data.get("operations_detected", []),
            "read_write_ratio": _compute_rw_ratio(svc_cost),
            "category": kb.get("category", ""),
        }

        # Identify issues
        issues = []
        if svc_cost.get("write_cost", 0) > svc_cost.get("read_cost", 0) * 3:
            issues.append("Write-heavy workload — consider batching writes to reduce WRU/WCU costs")
        if metrics.get("latency_ms", {}).get("p99", 0) > 500:
            issues.append("High p99 latency detected — consider caching layer or query optimization")
        if metrics.get("error_rate_percent", 0) > 1.0:
            issues.append("Elevated error rate — may indicate throttling or misconfigured capacity")

        finding["issues"] = issues
        findings.append(finding)

        for tip in tips[:3]:
            saving_pct = 0.15 if "Reserve" in tip else (0.25 if "switch" in tip.lower() or "Glacier" in tip else 0.10)
            saving_amt = round(monthly * saving_pct, 2)
            estimated_savings += saving_amt
            recommendations.append({
                "service": svc_name,
                "action": tip,
                "estimated_monthly_saving_usd": saving_amt,
                "priority": "high" if saving_amt > 20 else ("medium" if saving_amt > 5 else "low"),
            })

    # Use LLM to generate narrative summary
    prompt = f"""You are a cloud cost optimization expert analyzing {service_name}.

Usage data:
- AWS Services: {', '.join(aws_services)}
- Total Monthly Cost: ${total_cost:.2f}
- TPS: avg={metrics.get('tps', {}).get('average', 0)}, peak={metrics.get('tps', {}).get('peak', 0)}
- Latency p99: {metrics.get('latency_ms', {}).get('p99', 0):.1f}ms
- Error rate: {metrics.get('error_rate_percent', 0):.2f}%

Top recommendations identified:
{chr(10).join(f"- [{r['service']}] {r['action']} (save ${r['estimated_monthly_saving_usd']:.2f}/mo)" for r in recommendations[:5])}

Write a 3-4 sentence executive summary of the cost optimization opportunities for this microservice. 
Be specific, data-driven, and actionable. Mention total potential savings."""

    try:
        summary = gemini_client.client.models.generate_content(
            model=gemini_client.model,
            contents=prompt,
        ).text if gemini_client.enabled else _build_fallback_summary(service_name, total_cost, estimated_savings, aws_services)
    except Exception:
        summary = _build_fallback_summary(service_name, total_cost, estimated_savings, aws_services)

    recommendations.sort(key=lambda r: r["estimated_monthly_saving_usd"], reverse=True)

    return {
        "service_name": service_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "total_monthly_cost_usd": total_cost,
        "estimated_monthly_savings_usd": round(estimated_savings, 2),
        "savings_percentage": round((estimated_savings / total_cost * 100) if total_cost > 0 else 0, 1),
        "findings": findings,
        "recommendations": recommendations,
        "usage_pattern_data": usage_pattern_data,
    }


def _compute_rw_ratio(cost: dict) -> str:
    r = cost.get("read_cost", 0)
    w = cost.get("write_cost", 0)
    if r + w == 0:
        return "unknown"
    read_pct = round(r / (r + w) * 100)
    return f"{read_pct}% read / {100 - read_pct}% write"


def _build_fallback_summary(service: str, total: float, savings: float, services: list[str]) -> str:
    return (
        f"{service} currently spends ${total:.2f}/month across {', '.join(services)}. "
        f"Analysis identified approximately ${savings:.2f}/month in optimization potential "
        f"({round(savings / total * 100) if total > 0 else 0}% reduction). "
        f"Key opportunities include storage class optimization, right-sizing, and operation batching. "
        f"Implementing the top recommendations could reduce costs within 30 days."
    )