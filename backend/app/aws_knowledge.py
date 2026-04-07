"""
AWS Service Knowledge Base.
Provides structured information to help the LLM reason about:
- When to use which AWS service
- Cost characteristics
- Performance tradeoffs
- Migration paths
"""
from __future__ import annotations

AWS_SERVICE_KNOWLEDGE: dict[str, dict] = {
    "DynamoDB": {
        "category": "NoSQL Database",
        "when_to_use": [
            "Need single-digit millisecond latency at any scale",
            "Key-value or simple document access patterns",
            "Serverless or auto-scaling workloads with unpredictable traffic",
            "Global tables for multi-region active-active replication",
        ],
        "when_not_to_use": [
            "Complex relational queries with joins",
            "OLAP / analytical workloads (use Redshift or Athena instead)",
            "Large objects > 400KB per item",
        ],
        "cost_model": {
            "billing_modes": ["On-Demand (pay-per-request)", "Provisioned (reserve capacity)"],
            "key_costs": ["Read Request Units (RRU)", "Write Request Units (WRU)", "Storage ($0.25/GB/month)", "Backup", "Streams"],
            "optimization_tips": [
                "Switch to on-demand if traffic is unpredictable to avoid over-provisioning",
                "Use DynamoDB Accelerator (DAX) to cache hot reads instead of paying for repeated RRUs",
                "Compress large attribute values to reduce item size and storage costs",
                "Enable TTL to auto-expire old items and reduce storage costs for free",
                "Use batch operations (BatchGetItem/BatchWriteItem) to reduce round trips",
            ],
        },
        "alternatives": {"cheaper_for_relational": "Aurora Serverless", "cheaper_for_analytics": "Athena + S3"},
    },
    "S3": {
        "category": "Object Storage",
        "when_to_use": [
            "Store any type of file: images, logs, backups, datasets",
            "Static website hosting",
            "Data lake foundation",
            "Archival with Glacier storage classes",
        ],
        "when_not_to_use": [
            "Frequent small file writes (use EFS or EBS instead)",
            "Low-latency database access patterns",
        ],
        "cost_model": {
            "billing_modes": ["Standard", "Infrequent Access (IA)", "Glacier"],
            "key_costs": ["Storage per GB", "GET/HEAD requests ($0.0004/1000)", "PUT/POST/COPY ($0.005/1000)", "Data transfer out"],
            "optimization_tips": [
                "Enable S3 Intelligent-Tiering for files with unknown access patterns",
                "Set lifecycle policies to move old data to Glacier (saves up to 80%)",
                "Use S3 Transfer Acceleration only when needed — it adds cost",
                "Enable S3 Inventory + Storage Lens to identify unused buckets",
                "Compress files before storage to reduce storage costs",
            ],
        },
        "alternatives": {"cheaper_for_frequent_access": "EFS", "cheaper_for_archive": "S3 Glacier Deep Archive"},
    },
    "Lambda": {
        "category": "Serverless Compute",
        "when_to_use": [
            "Event-driven workloads (S3 triggers, SQS consumers, API handlers)",
            "Short-lived functions < 15 minutes",
            "Unpredictable or spiky traffic",
            "Microservice glue code",
        ],
        "when_not_to_use": [
            "Long-running tasks > 15 minutes",
            "High-throughput sustained compute (use ECS/EC2)",
            "Stateful services needing persistent connections",
        ],
        "cost_model": {
            "billing_modes": ["Pay-per-invocation", "Provisioned Concurrency (pre-warmed)"],
            "key_costs": ["Invocations ($0.20/million)", "Duration (GB-seconds)", "Provisioned Concurrency"],
            "optimization_tips": [
                "Right-size memory — Lambda charges by GB-second, more memory = faster execution but more cost per ms",
                "Use ARM/Graviton2 architecture for up to 20% cost savings",
                "Avoid Provisioned Concurrency unless cold starts are a real issue",
                "Bundle dependencies tightly to reduce cold start times",
                "Use Lambda Power Tuning to find the optimal memory configuration",
            ],
        },
        "alternatives": {"cheaper_for_sustained": "ECS Fargate Spot", "cheaper_for_batch": "AWS Batch"},
    },
    "RDS": {
        "category": "Relational Database",
        "when_to_use": [
            "Relational data with ACID transactions",
            "Complex joins and SQL queries",
            "Existing SQL workloads being migrated",
        ],
        "when_not_to_use": [
            "Key-value access patterns (use DynamoDB)",
            "Time-series data (use Timestream)",
            "Extremely large datasets needing horizontal scaling",
        ],
        "cost_model": {
            "billing_modes": ["On-Demand instances", "Reserved Instances (1yr/3yr)", "Aurora Serverless"],
            "key_costs": ["Instance hours", "Storage (gp2/gp3/io1)", "I/O requests", "Backup storage", "Data transfer"],
            "optimization_tips": [
                "Switch from gp2 to gp3 storage — same performance, up to 20% cheaper",
                "Use Reserved Instances for predictable workloads (saves up to 60%)",
                "Enable Aurora Serverless v2 for variable workloads to avoid idle costs",
                "Right-size instances using CloudWatch metrics (CPU, connections)",
                "Use read replicas to offload read traffic from the primary instance",
            ],
        },
        "alternatives": {"cheaper_for_variable": "Aurora Serverless v2", "cheaper_for_analytics": "Redshift"},
    },
    "APIGateway": {
        "category": "API Management",
        "when_to_use": ["Expose Lambda or HTTP backends as REST/HTTP/WebSocket APIs", "API versioning and throttling"],
        "when_not_to_use": ["High-throughput, low-latency APIs (use ALB + ECS instead)", "Simple internal service mesh (use App Mesh or service discovery)"],
        "cost_model": {
            "key_costs": ["API calls ($3.50/million for REST)", "Data transfer out", "Cache (optional)"],
            "optimization_tips": [
                "Prefer HTTP API over REST API — up to 70% cheaper for simple use cases",
                "Enable caching for frequently accessed endpoints",
                "Use usage plans and throttling to prevent runaway costs",
            ],
        },
        "alternatives": {"cheaper_for_high_throughput": "ALB", "cheaper_for_simple_http": "HTTP API Gateway"},
    },
}


def get_service_info(aws_service_name: str) -> dict:
    """Return knowledge base entry for an AWS service."""
    return AWS_SERVICE_KNOWLEDGE.get(aws_service_name, {
        "category": "AWS Service",
        "when_to_use": ["Refer to AWS documentation for specific use cases"],
        "cost_model": {"optimization_tips": ["Review AWS Cost Explorer for actual costs"]},
    })


def get_all_service_names() -> list[str]:
    return list(AWS_SERVICE_KNOWLEDGE.keys())


def get_optimization_tips(aws_service_name: str) -> list[str]:
    info = get_service_info(aws_service_name)
    return info.get("cost_model", {}).get("optimization_tips", [])