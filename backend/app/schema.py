"""
Unified Schema Assembler - Merges all module outputs into one validated JSON.

This module provides:
- build_unified_report(): Assembles codebase, metrics, costs, and AWS info into unified report
- validate_schema(): Validates the unified report structure
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional


def build_unified_report(
    codebase: dict,
    metrics: dict,
    costs: dict,
    aws_info: Optional[dict] = None,
) -> dict:
    """
    Assemble a unified report from all module outputs.
    
    Args:
        codebase: Output from codebase_analyzer.scan() or get_mock_codebase_analysis()
        metrics: Output from observability_client.get_service_metrics()
        costs: Output from cost_aggregator.get_monthly_costs()
        aws_info: Optional output from aws_service_knowledge functions
    
    Returns:
        Unified report dict matching the schema
    """
    # Extract codebase analysis
    codebase_analysis = {
        "repo_path": codebase.get("repo_path", "unknown"),
        "scanned_files": codebase.get("scanned_files", 0),
        "cloud_services_found": codebase.get("cloud_services", []),
        "service_summary": codebase.get("service_summary", {}),
    }
    
    # Build observability section
    observability = {}
    
    # If metrics is a single service metrics dict
    if "metrics" in metrics and "service" in metrics:
        service_name = metrics["service"]
        observability[service_name] = {
            "metrics": metrics.get("metrics", {}),
            "cloud_service_utilization": metrics.get("cloud_service_utilization", {}),
        }
    # If metrics is a dict of multiple services
    elif isinstance(metrics, dict):
        for service_name, service_metrics in metrics.items():
            if isinstance(service_metrics, dict):
                observability[service_name] = {
                    "metrics": service_metrics.get("metrics", service_metrics),
                    "cloud_service_utilization": service_metrics.get("cloud_service_utilization", {}),
                }
    
    # Build cost analysis section
    cost_analysis = {
        "period": costs.get("period", {}),
        "currency": costs.get("currency", "USD"),
        "total_cost": costs.get("total_cost", 0.0),
        "by_service": costs.get("by_service", {}),
    }
    
    # Build AWS service insights section
    aws_service_insights = {}
    if aws_info:
        if isinstance(aws_info, dict) and "service_key" in aws_info:
            # Single service info
            service_key = aws_info.get("service_key", "unknown")
            aws_service_insights[service_key] = {
                "catalog_info": aws_info,
                "estimated_cost": aws_info.get("estimated_cost", {}),
            }
        elif isinstance(aws_info, dict):
            # Multiple services info
            for service_key, info in aws_info.items():
                if isinstance(info, dict):
                    aws_service_insights[service_key] = {
                        "catalog_info": info,
                        "estimated_cost": info.get("estimated_cost", {}),
                    }
    
    # Build recommendations input section
    recommendations_input = _build_recommendations_input(
        cost_analysis, observability
    )
    
    # Assemble final report
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "codebase_analysis": codebase_analysis,
        "observability": observability,
        "cost_analysis": cost_analysis,
        "aws_service_insights": aws_service_insights,
        "recommendations_input": recommendations_input,
    }
    
    return report


def _build_recommendations_input(
    cost_analysis: dict,
    observability: dict,
) -> dict:
    """
    Build the recommendations input section based on cost and observability data.
    
    Identifies:
    - High cost services (>$50/month)
    - Underutilized services (CPU < 20%)
    - High latency services (p99 > 500ms)
    - High error rate services (> 1%)
    """
    high_cost_services = []
    underutilized_services = []
    high_latency_services = []
    high_error_rate_services = []
    
    # Analyze costs
    by_service = cost_analysis.get("by_service", {})
    for service_name, cost_data in by_service.items():
        total_cost = cost_data.get("total_cost", 0.0)
        if total_cost > 50:
            high_cost_services.append({
                "service": service_name,
                "monthly_cost_usd": total_cost,
            })
    
    # Analyze observability metrics
    for service_name, obs_data in observability.items():
        metrics = obs_data.get("metrics", {})
        
        # Check CPU utilization
        cpu = metrics.get("cpu_utilization_pct", {})
        cpu_avg = cpu.get("avg", 100)
        if cpu_avg < 20 and cpu_avg > 0:
            underutilized_services.append({
                "service": service_name,
                "cpu_utilization_pct": cpu_avg,
            })
        
        # Check latency
        p99 = metrics.get("latency_p99_ms", {})
        p99_avg = p99.get("avg", 0)
        if p99_avg > 500:
            high_latency_services.append({
                "service": service_name,
                "latency_p99_ms": p99_avg,
            })
        
        # Check error rate
        error_rate = metrics.get("error_rate_pct", {})
        error_avg = error_rate.get("avg", 0)
        if error_avg > 1:
            high_error_rate_services.append({
                "service": service_name,
                "error_rate_pct": error_avg,
            })
    
    return {
        "high_cost_services": high_cost_services,
        "underutilized_services": underutilized_services,
        "high_latency_services": high_latency_services,
        "high_error_rate_services": high_error_rate_services,
    }


def validate_schema(report: dict) -> bool:
    """
    Validate that a report matches the expected schema.
    
    Args:
        report: The report dict to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_top_level_keys = [
        "schema_version",
        "generated_at",
        "codebase_analysis",
        "observability",
        "cost_analysis",
        "aws_service_insights",
        "recommendations_input",
    ]
    
    # Check top-level keys
    for key in required_top_level_keys:
        if key not in report:
            return False
    
    # Validate codebase_analysis
    codebase = report.get("codebase_analysis", {})
    if not isinstance(codebase.get("scanned_files"), int):
        return False
    if not isinstance(codebase.get("cloud_services_found"), list):
        return False
    if not isinstance(codebase.get("service_summary"), dict):
        return False
    
    # Validate cost_analysis
    costs = report.get("cost_analysis", {})
    if not isinstance(costs.get("total_cost"), (int, float)):
        return False
    if not isinstance(costs.get("by_service"), dict):
        return False
    
    # Validate recommendations_input
    recs = report.get("recommendations_input", {})
    for key in ["high_cost_services", "underutilized_services", 
                "high_latency_services", "high_error_rate_services"]:
        if not isinstance(recs.get(key), list):
            return False
    
    return True


def save_report(report: dict, filepath: str = "unified_report.json") -> str:
    """
    Save a unified report to a JSON file.
    
    Args:
        report: The report dict to save
        filepath: Output file path
    
    Returns:
        The filepath where the report was saved
    """
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    return filepath


def load_report(filepath: str) -> dict:
    """
    Load a unified report from a JSON file.
    
    Args:
        filepath: Path to the report file
    
    Returns:
        The loaded report dict
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def create_sample_report() -> dict:
    """
    Create a sample unified report for testing.
    
    Returns:
        A sample report dict
    """
    # Import mock data functions
    try:
        from .codebase_analyzer_v2 import get_mock_codebase_analysis
        from .observability_client import get_mock_metrics
        from .cost_aggregator_v2 import get_mock_costs
        from .aws_service_knowledge import get_service_info
    except ImportError:
        from codebase_analyzer_v2 import get_mock_codebase_analysis
        from observability_client import get_mock_metrics
        from cost_aggregator_v2 import get_mock_costs
        from aws_service_knowledge import get_service_info
    
    codebase = get_mock_codebase_analysis()
    metrics = get_mock_metrics("s3")
    costs = get_mock_costs()
    
    # Get info for each service in the cost breakdown
    aws_info = {}
    for service_name in costs.get("by_service", {}).keys():
        info = get_service_info(service_name)
        if "not_found" not in info:
            aws_info[service_name] = info
    
    return build_unified_report(codebase, metrics, costs, aws_info)


if __name__ == "__main__":
    # Create and validate a sample report
    report = create_sample_report()
    
    print("=== Sample Unified Report ===")
    print(json.dumps(report, indent=2, default=str)[:2000] + "...")
    
    print("\n=== Schema Validation ===")
    is_valid = validate_schema(report)
    print(f"Valid: {is_valid}")
    
    # Save to file
    filepath = save_report(report)
    print(f"\nReport saved to: {filepath}")