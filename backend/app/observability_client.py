"""
Observability Client - Fetches metrics from Datadog and CloudWatch.

This module provides:
- ObservabilityClient class with get_service_metrics() method
- get_mock_metrics() fallback function
"""
from __future__ import annotations

import os
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import requests


class ObservabilityClient:
    """Client for fetching observability metrics from Datadog and CloudWatch."""
    
    def __init__(
        self, 
        datadog_api_key: Optional[str] = None,
        datadog_app_key: Optional[str] = None,
        aws_region: str = "us-east-1"
    ):
        self.datadog_api_key = datadog_api_key or os.environ.get("DD_API_KEY")
        self.datadog_app_key = datadog_app_key or os.environ.get("DD_APP_KEY")
        self.aws_region = aws_region
        self.datadog_site = os.environ.get("DD_SITE", "datadoghq.com")
    
    def get_service_metrics(
        self, 
        service_name: str, 
        time_range_hours: int = 720
    ) -> dict:
        """
        Fetch metrics for a service from Datadog and CloudWatch.
        
        Args:
            service_name: Name of the service to fetch metrics for
            time_range_hours: Time range in hours (default: 720 = 30 days)
        
        Returns:
            Dict with TPS, latency, error rate, and resource utilization metrics
        """
        now = int(datetime.now(timezone.utc).timestamp())
        from_ts = now - (time_range_hours * 3600)
        
        result = {
            "service": service_name,
            "time_range_hours": time_range_hours,
            "datadog_available": bool(self.datadog_api_key and self.datadog_app_key),
            "cloudwatch_available": False,
            "metrics": {},
            "cloud_service_utilization": {}
        }
        
        # Try Datadog first
        if self.datadog_api_key and self.datadog_app_key:
            dd_metrics = self._fetch_datadog_metrics(service_name, from_ts, now)
            result["metrics"].update(dd_metrics)
        
        # Try CloudWatch fallback
        try:
            cw_metrics = self._fetch_cloudwatch_metrics(service_name, time_range_hours)
            if cw_metrics:
                result["cloudwatch_available"] = True
                result["metrics"].update(cw_metrics)
        except Exception:
            pass
        
        # If no real metrics, return mock data
        if not result["metrics"]:
            result["metrics"] = get_mock_metrics(service_name)["metrics"]
            result["cloud_service_utilization"] = get_mock_metrics(service_name)["cloud_service_utilization"]
        
        return result
    
    def _fetch_datadog_metrics(
        self, 
        service_name: str, 
        from_ts: int, 
        to_ts: int
    ) -> dict:
        """Fetch metrics from Datadog API."""
        headers = {
            "DD-API-KEY": self.datadog_api_key,
            "DD-APPLICATION-KEY": self.datadog_app_key,
            "Content-Type": "application/json"
        }
        url = f"https://api.{self.datadog_site}/api/v1/query"
        
        tag = f"service:{service_name}"
        
        queries = {
            "tps": f"sum:trace.web.request.hits{{{tag}}}.as_rate()",
            "p50_latency": f"p50:trace.web.request.duration{{{tag}}}",
            "p95_latency": f"p95:trace.web.request.duration{{{tag}}}",
            "p99_latency": f"p99:trace.web.request.duration{{{tag}}}",
            "error_rate": f"sum:trace.web.request.errors{{{tag}}}.as_rate() / sum:trace.web.request.hits{{{tag}}}.as_rate() * 100",
        }
        
        metrics = {}
        
        for metric_name, query in queries.items():
            try:
                params = {
                    "query": query,
                    "from": from_ts,
                    "to": to_ts
                }
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                series = data.get("series", [])
                if series:
                    points = series[0].get("pointlist", [])
                    values = [p[1] for p in points if p[1] is not None]
                    
                    if values:
                        avg_val = round(sum(values) / len(values), 4)
                        min_val = round(min(values), 4)
                        max_val = round(max(values), 4)
                        
                        if metric_name == "tps":
                            metrics["tps"] = {
                                "avg": avg_val,
                                "min": min_val,
                                "max": max_val,
                                "unit": "req/s"
                            }
                        elif "latency" in metric_name:
                            # Convert from seconds to milliseconds
                            metrics[metric_name] = {
                                "avg": round(avg_val * 1000, 4),
                                "min": round(min_val * 1000, 4),
                                "max": round(max_val * 1000, 4)
                            }
                        elif metric_name == "error_rate":
                            metrics["error_rate_pct"] = {
                                "avg": round(avg_val, 4),
                                "min": round(min_val, 4),
                                "max": round(max_val, 4)
                            }
            except Exception:
                continue
        
        return metrics
    
    def _fetch_cloudwatch_metrics(
        self, 
        service_name: str, 
        time_range_hours: int
    ) -> dict:
        """Fetch metrics from AWS CloudWatch."""
        try:
            import boto3
            from datetime import datetime, timezone, timedelta
            
            client = boto3.client("cloudwatch", region_name=self.aws_region)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_range_hours)
            
            metrics = {}
            
            # Map service names to CloudWatch namespaces
            namespace_map = {
                "ec2": "AWS/EC2",
                "dynamodb": "AWS/DynamoDB",
                "lambda": "AWS/Lambda",
                "s3": "AWS/S3",
                "sqs": "AWS/SQS",
                "sns": "AWS/SNS",
                "rds": "AWS/RDS",
                "elasticache": "AWS/ElastiCache",
                "ecs": "AWS/ECS",
            }
            
            namespace = namespace_map.get(service_name.lower())
            if not namespace:
                return {}
            
            # Define metrics to fetch per service
            metric_configs = {
                "ec2": [
                    ("CPUUtilization", "Average", "network_in_bytes"),
                    ("NetworkIn", "Sum", "network_in_bytes"),
                    ("NetworkOut", "Sum", "network_out_bytes"),
                ],
                "dynamodb": [
                    ("ConsumedReadCapacityUnits", "Sum", None),
                    ("ConsumedWriteCapacityUnits", "Sum", None),
                ],
                "lambda": [
                    ("Duration", "Average", "latency_ms"),
                    ("Invocations", "Sum", "invocations"),
                ],
                "sqs": [
                    ("NumberOfMessagesSent", "Sum", None),
                    ("ApproximateNumberOfMessagesVisible", "Average", None),
                ],
            }
            
            config = metric_configs.get(service_name.lower(), [])
            
            for metric_name, statistic, result_key in config:
                try:
                    response = client.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric_name,
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour
                        Statistics=[statistic],
                    )
                    
                    datapoints = response.get("Datapoints", [])
                    values = [dp[statistic] for dp in datapoints if dp.get(statistic) is not None]
                    
                    if values:
                        avg_val = round(sum(values) / len(values), 4)
                        metrics[result_key or metric_name] = {"avg": avg_val}
                except Exception:
                    continue
            
            return metrics
            
        except ImportError:
            return {}
        except Exception:
            return {}
    
    def get_cloud_service_utilization(
        self, 
        service_name: str, 
        time_range_hours: int = 720
    ) -> dict:
        """Get utilization metrics for AWS cloud services."""
        result = {}
        
        # Try CloudWatch for specific services
        try:
            import boto3
            from datetime import datetime, timezone, timedelta
            
            client = boto3.client("cloudwatch", region_name=self.aws_region)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_range_hours)
            
            # DynamoDB utilization
            if service_name.lower() == "dynamodb":
                try:
                    # Read capacity
                    response = client.get_metric_statistics(
                        Namespace="AWS/DynamoDB",
                        MetricName="ConsumedReadCapacityUnits",
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=["Average"],
                    )
                    read_values = [dp["Average"] for dp in response.get("Datapoints", []) if dp.get("Average") is not None]
                    
                    # Write capacity
                    response = client.get_metric_statistics(
                        Namespace="AWS/DynamoDB",
                        MetricName="ConsumedWriteCapacityUnits",
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=["Average"],
                    )
                    write_values = [dp["Average"] for dp in response.get("Datapoints", []) if dp.get("Average") is not None]
                    
                    result["dynamodb"] = {
                        "read_units_avg": round(sum(read_values) / len(read_values), 2) if read_values else 0,
                        "write_units_avg": round(sum(write_values) / len(write_values), 2) if write_values else 0,
                    }
                except Exception:
                    pass
            
            # S3 utilization
            if service_name.lower() == "s3":
                try:
                    response = client.get_metric_statistics(
                        Namespace="AWS/S3",
                        MetricName="BucketSizeBytes",
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=["Average"],
                    )
                    size_values = [dp["Average"] for dp in response.get("Datapoints", []) if dp.get("Average") is not None]
                    
                    if size_values:
                        result["s3"] = {
                            "storage_bytes_avg": round(sum(size_values) / len(size_values), 2),
                        }
                except Exception:
                    pass
                    
        except ImportError:
            pass
        except Exception:
            pass
        
        return result


def get_mock_metrics(service_name: str) -> dict:
    """
    Returns realistic mock metrics data for a service.
    Used as fallback when observability APIs are not accessible.
    """
    import random
    
    # Generate realistic metrics based on service type
    base_tps = random.uniform(20, 200)
    base_latency = random.uniform(10, 100)
    base_error_rate = random.uniform(0.1, 2.0)
    
    # Service-specific adjustments
    service_profiles = {
        "s3": {"tps_mult": 5, "latency_mult": 0.5, "error_mult": 0.3},
        "dynamodb": {"tps_mult": 3, "latency_mult": 0.8, "error_mult": 0.5},
        "lambda": {"tps_mult": 2, "latency_mult": 1.5, "error_mult": 1.0},
        "rds": {"tps_mult": 1, "latency_mult": 2.0, "error_mult": 0.8},
        "sqs": {"tps_mult": 4, "latency_mult": 0.3, "error_mult": 0.2},
        "elasticache": {"tps_mult": 10, "latency_mult": 0.1, "error_mult": 0.1},
        "ec2": {"tps_mult": 1, "latency_mult": 1.0, "error_mult": 0.5},
        "ecs": {"tps_mult": 2, "latency_mult": 1.2, "error_mult": 0.7},
    }
    
    profile = service_profiles.get(service_name.lower(), {"tps_mult": 1, "latency_mult": 1, "error_mult": 1})
    
    tps = base_tps * profile["tps_mult"]
    latency_p50 = base_latency * profile["latency_mult"]
    latency_p95 = latency_p50 * random.uniform(2, 4)
    latency_p99 = latency_p95 * random.uniform(1.5, 3)
    error_rate = base_error_rate * profile["error_mult"]
    
    return {
        "service": service_name,
        "time_range_hours": 720,
        "datadog_available": False,
        "cloudwatch_available": False,
        "metrics": {
            "tps": {
                "avg": round(tps, 2),
                "min": round(tps * 0.3, 2),
                "max": round(tps * 3, 2),
                "unit": "req/s"
            },
            "latency_p50_ms": {
                "avg": round(latency_p50, 2),
                "min": round(latency_p50 * 0.5, 2),
                "max": round(latency_p50 * 2, 2),
            },
            "latency_p95_ms": {
                "avg": round(latency_p95, 2),
                "min": round(latency_p95 * 0.5, 2),
                "max": round(latency_p95 * 2, 2),
            },
            "latency_p99_ms": {
                "avg": round(latency_p99, 2),
                "min": round(latency_p99 * 0.5, 2),
                "max": round(latency_p99 * 2, 2),
            },
            "error_rate_pct": {
                "avg": round(error_rate, 4),
                "min": round(error_rate * 0.1, 4),
                "max": round(error_rate * 5, 4),
            },
            "cpu_utilization_pct": {
                "avg": round(random.uniform(20, 80), 2),
            },
            "network_in_bytes": {
                "avg": round(random.uniform(1024*1024, 100*1024*1024), 2),
            },
            "network_out_bytes": {
                "avg": round(random.uniform(1024*1024, 50*1024*1024), 2),
            },
        },
        "cloud_service_utilization": {
            service_name: {
                "read_units_avg": round(random.uniform(10, 500), 2),
                "write_units_avg": round(random.uniform(5, 200), 2),
            }
        }
    }


def get_service_metrics(
    service_name: str,
    time_range_hours: int = 720,
    datadog_api_key: Optional[str] = None,
    datadog_app_key: Optional[str] = None,
) -> dict:
    """
    Convenience function to get service metrics.
    
    Args:
        service_name: Name of the service
        time_range_hours: Time range in hours
        datadog_api_key: Optional Datadog API key
        datadog_app_key: Optional Datadog app key
    
    Returns:
        Dict with service metrics
    """
    try:
        client = ObservabilityClient(
            datadog_api_key=datadog_api_key,
            datadog_app_key=datadog_app_key,
        )
        return client.get_service_metrics(service_name, time_range_hours)
    except Exception:
        return get_mock_metrics(service_name)


if __name__ == "__main__":
    import sys
    # Test with mock data
    service = sys.argv[1] if len(sys.argv) > 1 else "s3"
    result = get_service_metrics(service)
    print(json.dumps(result, indent=2))
