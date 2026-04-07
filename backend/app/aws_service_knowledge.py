"""
AWS Service Knowledge Base - Static and dynamic catalog of AWS services.

This module provides:
- AWS_SERVICE_CATALOG: Comprehensive service information
- get_service_info(): Look up service details
- compare_services(): Find best services for a use case
- estimate_cost(): Calculate estimated costs based on usage
"""
from __future__ import annotations

import json
from typing import Any, Optional


# Comprehensive AWS Service Catalog
AWS_SERVICE_CATALOG: dict[str, dict[str, Any]] = {
    "s3": {
        "full_name": "Amazon Simple Storage Service",
        "category": "storage",
        "description": "Object storage service offering industry-leading scalability, data availability, security, and performance.",
        "best_for": [
            "Store any type of file: images, logs, backups, datasets",
            "Static website hosting",
            "Data lake foundation",
            "Archival with Glacier storage classes",
            "Large file storage with infrequent access",
        ],
        "not_suitable_for": [
            "Frequent small file writes (use EFS or EBS instead)",
            "Low-latency database access patterns",
            "File systems requiring POSIX compliance",
        ],
        "pricing_model": "tiered",
        "cost_drivers": [
            "Storage volume per GB",
            "GET/HEAD requests ($0.0004/1000)",
            "PUT/POST/COPY/DELETE requests ($0.005/1000)",
            "Data transfer out to internet",
            "Storage class (Standard vs IA vs Glacier)",
        ],
        "cost_optimization_tips": [
            "Enable S3 Intelligent-Tiering for files with unknown access patterns",
            "Set lifecycle policies to move old data to Glacier (saves up to 80%)",
            "Use S3 Transfer Acceleration only when needed — it adds cost",
            "Enable S3 Inventory + Storage Lens to identify unused buckets",
            "Compress files before storage to reduce storage costs",
            "Use CloudFront for frequently accessed content to reduce S3 request costs",
        ],
        "typical_monthly_cost_usd": {
            "small": 5.0,
            "medium": 50.0,
            "large": 500.0,
        },
        "comparable_services": ["ebs", "efs", "glacier"],
    },
    "dynamodb": {
        "full_name": "Amazon DynamoDB",
        "category": "database",
        "description": "Fast, flexible NoSQL database service for single-digit millisecond performance at any scale.",
        "best_for": [
            "Need single-digit millisecond latency at any scale",
            "Key-value or simple document access patterns",
            "Serverless or auto-scaling workloads with unpredictable traffic",
            "Global tables for multi-region active-active replication",
            "Session stores and shopping carts",
        ],
        "not_suitable_for": [
            "Complex relational queries with joins",
            "OLAP / analytical workloads (use Redshift or Athena instead)",
            "Large objects > 400KB per item",
            "Full-text search requirements",
        ],
        "pricing_model": "per_request",
        "cost_drivers": [
            "Read Request Units (RRU) - $0.25/million on-demand",
            "Write Request Units (WRU) - $1.25/million on-demand",
            "Storage ($0.25/GB/month)",
            "Backup storage beyond free tier",
            "DynamoDB Streams",
            "Global Tables replication",
        ],
        "cost_optimization_tips": [
            "Switch to on-demand if traffic is unpredictable to avoid over-provisioning",
            "Use DynamoDB Accelerator (DAX) to cache hot reads instead of paying for repeated RRUs",
            "Compress large attribute values to reduce item size and storage costs",
            "Enable TTL to auto-expire old items and reduce storage costs for free",
            "Use batch operations (BatchGetItem/BatchWriteItem) to reduce round trips",
            "Consider provisioned capacity with auto-scaling for predictable workloads",
        ],
        "typical_monthly_cost_usd": {
            "small": 10.0,
            "medium": 100.0,
            "large": 1000.0,
        },
        "comparable_services": ["rds", "elasticache", "documentdb"],
    },
    "rds": {
        "full_name": "Amazon Relational Database Service",
        "category": "database",
        "description": "Managed relational database service supporting MySQL, PostgreSQL, MariaDB, Oracle, and SQL Server.",
        "best_for": [
            "Relational data with ACID transactions",
            "Complex joins and SQL queries",
            "Existing SQL workloads being migrated",
            "Applications requiring specific database engines",
        ],
        "not_suitable_for": [
            "Key-value access patterns (use DynamoDB)",
            "Time-series data (use Timestream)",
            "Extremely large datasets needing horizontal scaling",
            "Serverless requirements (consider Aurora Serverless)",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Instance hours (varies by instance type)",
            "Storage (gp2/gp3/io1) per GB-month",
            "I/O requests (for io1/io2 volumes)",
            "Backup storage beyond free tier",
            "Data transfer out",
        ],
        "cost_optimization_tips": [
            "Switch from gp2 to gp3 storage — same performance, up to 20% cheaper",
            "Use Reserved Instances for predictable workloads (saves up to 60%)",
            "Enable Aurora Serverless v2 for variable workloads to avoid idle costs",
            "Right-size instances using CloudWatch metrics (CPU, connections)",
            "Use read replicas to offload read traffic from the primary instance",
            "Enable Performance Insights to identify inefficient queries",
        ],
        "typical_monthly_cost_usd": {
            "small": 20.0,
            "medium": 150.0,
            "large": 800.0,
        },
        "comparable_services": ["dynamodb", "aurora", "redshift"],
    },
    "elasticache": {
        "full_name": "Amazon ElastiCache",
        "category": "database",
        "description": "Fully managed in-memory data store service supporting Redis and Memcached.",
        "best_for": [
            "Caching database queries and API responses",
            "Session management for web applications",
            "Real-time leaderboards and counters",
            "Pub/sub messaging patterns",
            "Low-latency data access requirements",
        ],
        "not_suitable_for": [
            "Persistent data storage (use RDS or DynamoDB)",
            "Large data sets that don't fit in memory",
            "Complex queries requiring SQL",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Node hours (varies by node type)",
            "Data transfer out",
            "Backup storage (Redis only)",
        ],
        "cost_optimization_tips": [
            "Use smaller nodes with cluster mode for horizontal scaling",
            "Choose Memcached over Redis for simple caching (cheaper)",
            "Use Reserved Nodes for predictable workloads (saves up to 40%)",
            "Monitor cache hit rates to right-size your cluster",
            "Use Auto Scaling for Redis clusters based on CPU utilization",
        ],
        "typical_monthly_cost_usd": {
            "small": 15.0,
            "medium": 80.0,
            "large": 400.0,
        },
        "comparable_services": ["dynamodb", "memorydb"],
    },
    "lambda": {
        "full_name": "AWS Lambda",
        "category": "compute",
        "description": "Serverless compute service that runs code in response to events without provisioning servers.",
        "best_for": [
            "Event-driven workloads (S3 triggers, SQS consumers, API handlers)",
            "Short-lived functions < 15 minutes",
            "Unpredictable or spiky traffic",
            "Microservice glue code",
            "Scheduled tasks (cron jobs)",
        ],
        "not_suitable_for": [
            "Long-running tasks > 15 minutes",
            "High-throughput sustained compute (use ECS/EC2)",
            "Stateful services needing persistent connections",
            "GPU-intensive workloads",
        ],
        "pricing_model": "per_request",
        "cost_drivers": [
            "Invocations ($0.20/million)",
            "Duration (GB-seconds) - $0.0000166667 per GB-second",
            "Provisioned Concurrency (pre-warmed instances)",
            "Data transfer out",
        ],
        "cost_optimization_tips": [
            "Right-size memory — Lambda charges by GB-second, more memory = faster execution but more cost per ms",
            "Use ARM/Graviton2 architecture for up to 20% cost savings",
            "Avoid Provisioned Concurrency unless cold starts are a real issue",
            "Bundle dependencies tightly to reduce cold start times",
            "Use Lambda Power Tuning to find the optimal memory configuration",
            "Combine functions to reduce total invocations",
        ],
        "typical_monthly_cost_usd": {
            "small": 1.0,
            "medium": 30.0,
            "large": 300.0,
        },
        "comparable_services": ["ec2", "ecs", "fargate", "batch"],
    },
    "ec2": {
        "full_name": "Amazon Elastic Compute Cloud",
        "category": "compute",
        "description": "Secure and resizable compute capacity in the cloud with full control over computing resources.",
        "best_for": [
            "Applications requiring full OS control",
            "Long-running stateful workloads",
            "GPU or specialized hardware requirements",
            "Predictable, sustained compute needs",
            "Custom networking configurations",
        ],
        "not_suitable_for": [
            "Highly variable or unpredictable workloads (use Lambda)",
            "Event-driven microservices",
            "Applications that can't tolerate restarts",
        ],
        "pricing_model": "on_demand",
        "cost_drivers": [
            "Instance hours (varies by instance type)",
            "EBS storage (gp2/gp3/io1/io2)",
            "Data transfer out",
            "Elastic IP addresses (when not attached)",
            "Load balancer hours + LCU",
        ],
        "cost_optimization_tips": [
            "Use Reserved Instances for predictable workloads (saves up to 72%)",
            "Use Spot Instances for fault-tolerant, flexible workloads (saves up to 90%)",
            "Right-size instances using CloudWatch metrics",
            "Use Savings Plans for flexible commitment discounts",
            "Stop unused instances and delete orphaned EBS volumes",
            "Use Auto Scaling groups to match capacity to demand",
        ],
        "typical_monthly_cost_usd": {
            "small": 10.0,
            "medium": 100.0,
            "large": 1000.0,
        },
        "comparable_services": ["lambda", "ecs", "fargate", "lightsail"],
    },
    "ecs": {
        "full_name": "Amazon Elastic Container Service",
        "category": "compute",
        "description": "Fully managed container orchestration service supporting Docker containers.",
        "best_for": [
            "Microservices architectures",
            "Container-based deployments",
            "Batch processing workloads",
            "Hybrid cloud deployments with ECS Anywhere",
        ],
        "not_suitable_for": [
            "Simple single-container applications",
            "Applications requiring Kubernetes-specific features",
            "Stateful applications without proper storage configuration",
        ],
        "pricing_model": "on_demand",
        "cost_drivers": [
            "EC2 instances (if using EC2 launch type)",
            "Fargate compute (vCPU-hours + memory-hours)",
            "Data transfer out",
            "EBS storage for EC2 launch type",
        ],
        "cost_optimization_tips": [
            "Use Fargate Spot for fault-tolerant workloads (saves up to 70%)",
            "Right-size task definitions to avoid over-provisioning",
            "Use EC2 launch type for predictable, high-utilization workloads",
            "Enable Service Auto Scaling based on CPU/memory utilization",
            "Use Graviton2-based instances for better price-performance",
        ],
        "typical_monthly_cost_usd": {
            "small": 15.0,
            "medium": 120.0,
            "large": 800.0,
        },
        "comparable_services": ["ec2", "lambda", "fargate", "eks"],
    },
    "sqs": {
        "full_name": "Amazon Simple Queue Service",
        "category": "messaging",
        "description": "Fully managed message queuing service for decoupling and scaling microservices and distributed systems.",
        "best_for": [
            "Decoupling microservices",
            "Asynchronous processing",
            "Buffering workloads",
            "Fan-out patterns with SNS",
            "Dead-letter queues for error handling",
        ],
        "not_suitable_for": [
            "Real-time streaming data (use Kinesis)",
            "Pub/sub patterns without fan-out (use SNS)",
            "Complex message routing",
        ],
        "pricing_model": "per_request",
        "cost_drivers": [
            "Requests ($0.40/million for standard, $0.50/million for FIFO)",
            "Data transfer out",
            "S3 storage for message payloads (large messages)",
        ],
        "cost_optimization_tips": [
            "Use batch operations (SendMessageBatch, ReceiveMessage with MaxMessages)",
            "Use long polling to reduce empty receives",
            "Choose Standard queues over FIFO when ordering isn't critical",
            "Set appropriate message retention period (default 4 days, max 14 days)",
            "Use dead-letter queues to avoid reprocessing failed messages",
        ],
        "typical_monthly_cost_usd": {
            "small": 0.50,
            "medium": 5.0,
            "large": 50.0,
        },
        "comparable_services": ["sns", "kinesis", "mq"],
    },
    "sns": {
        "full_name": "Amazon Simple Notification Service",
        "category": "messaging",
        "description": "Fully managed pub/sub messaging service for application-to-application and application-to-person communication.",
        "best_for": [
            "Pub/sub messaging patterns",
            "Fan-out to multiple subscribers",
            "Push notifications to mobile devices",
            "SMS and email notifications",
            "Event-driven architectures",
        ],
        "not_suitable_for": [
            "Point-to-point messaging (use SQS)",
            "Message ordering requirements (use Kinesis)",
            "High-throughput streaming data",
        ],
        "pricing_model": "per_request",
        "cost_drivers": [
            "Publish requests ($0.50/million)",
            "HTTP/HTTPS deliveries ($0.60/million)",
            "Email deliveries ($0.20/100 for standard, $1.00/100 for JSON)",
            "SMS deliveries (varies by country)",
            "Mobile push notifications ($0.00 for most platforms)",
        ],
        "cost_optimization_tips": [
            "Use HTTP/HTTPS subscriptions instead of email when possible",
            "Batch notifications when real-time delivery isn't required",
            "Filter messages at the subscription level to reduce downstream costs",
            "Use application-specific topics rather than broad topics",
        ],
        "typical_monthly_cost_usd": {
            "small": 0.50,
            "medium": 5.0,
            "large": 30.0,
        },
        "comparable_services": ["sqs", "eventbridge", "kinesis"],
    },
    "kinesis": {
        "full_name": "Amazon Kinesis",
        "category": "analytics",
        "description": "Platform for streaming data on AWS, including Kinesis Data Streams, Data Firehose, and Data Analytics.",
        "best_for": [
            "Real-time data streaming",
            "Log and event data collection",
            "Real-time analytics",
            "Clickstream analysis",
            "IoT data ingestion",
        ],
        "not_suitable_for": [
            "Simple message queuing (use SQS)",
            "Pub/sub patterns (use SNS)",
            "Batch data processing",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Shard hours ($0.015 per shard-hour)",
            "PUT payload units (per 25KB)",
            "Data retrieval (enhanced fan-out)",
            "Data Firehose data ingestion",
        ],
        "cost_optimization_tips": [
            "Use on-demand mode for unpredictable workloads",
            "Aggregate records before sending to reduce PUT costs",
            "Monitor shard utilization and reshard appropriately",
            "Use compression to reduce data volume",
            "Consider Data Firehose for simpler use cases (pay per GB)",
        ],
        "typical_monthly_cost_usd": {
            "small": 15.0,
            "medium": 100.0,
            "large": 500.0,
        },
        "comparable_services": ["msk", "sqs", "eventbridge"],
    },
    "api_gateway": {
        "full_name": "Amazon API Gateway",
        "category": "networking",
        "description": "Fully managed service for creating, publishing, maintaining, and securing APIs at any scale.",
        "best_for": [
            "Expose Lambda or HTTP backends as REST/HTTP/WebSocket APIs",
            "API versioning and throttling",
            "Authentication and authorization",
            "Request/response transformation",
            "API monetization",
        ],
        "not_suitable_for": [
            "High-throughput, low-latency APIs (use ALB + ECS instead)",
            "Simple internal service mesh (use App Mesh or service discovery)",
            "gRPC services (use ALB or App Mesh)",
        ],
        "pricing_model": "per_request",
        "cost_drivers": [
            "API calls ($3.50/million for REST, $1.00/million for HTTP)",
            "Data transfer out",
            "Caching (optional, varies by cache size)",
            "WebSocket messages ($0.25/million)",
        ],
        "cost_optimization_tips": [
            "Prefer HTTP API over REST API — up to 70% cheaper for simple use cases",
            "Enable caching for frequently accessed endpoints",
            "Use usage plans and throttling to prevent runaway costs",
            "Consider ALB for high-throughput internal APIs",
            "Monitor and optimize payload sizes to reduce data transfer costs",
        ],
        "typical_monthly_cost_usd": {
            "small": 3.50,
            "medium": 35.0,
            "large": 350.0,
        },
        "comparable_services": ["alb", "cloudfront", "appsync"],
    },
    "cloudfront": {
        "full_name": "Amazon CloudFront",
        "category": "networking",
        "description": "Fast content delivery network (CDN) service that securely delivers data, videos, applications, and APIs globally.",
        "best_for": [
            "Static asset delivery (images, CSS, JS)",
            "Video streaming",
            "API acceleration",
            "Global application performance",
            "DDoS protection with AWS Shield",
        ],
        "not_suitable_for": [
            "Dynamic content that can't be cached",
            "Internal-only applications",
            "Small-scale applications with local users",
        ],
        "pricing_model": "tiered",
        "cost_drivers": [
            "Data transfer out (varies by region)",
            "HTTP/HTTPS requests",
            "Invalidation requests ($0.005 per path)",
            "Real-time logs (optional)",
        ],
        "cost_optimization_tips": [
            "Set appropriate TTLs to maximize cache hit ratio",
            "Use cache policies to optimize caching behavior",
            "Enable compression for text-based content",
            "Use origin shield to reduce origin requests",
            "Monitor cache statistics and adjust TTLs accordingly",
        ],
        "typical_monthly_cost_usd": {
            "small": 1.0,
            "medium": 30.0,
            "large": 300.0,
        },
        "comparable_services": ["s3", "api_gateway", "global_accelerator"],
    },
    "aurora": {
        "full_name": "Amazon Aurora",
        "category": "database",
        "description": "MySQL and PostgreSQL-compatible relational database built for the cloud with performance and availability.",
        "best_for": [
            "MySQL/PostgreSQL workloads requiring high performance",
            "Global applications with Aurora Global Database",
            "Serverless database requirements",
            "High availability requirements",
            "Read-heavy workloads with Aurora Read Replicas",
        ],
        "not_suitable_for": [
            "Non-relational data (use DynamoDB)",
            "Simple key-value access patterns",
            "Workloads requiring specific RDS engine features",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Instance hours (Aurora instances)",
            "Storage (Aurora storage - $0.10/GB-month)",
            "I/O requests (for Aurora MySQL)",
            "Backup storage beyond free tier",
            "Data transfer out",
        ],
        "cost_optimization_tips": [
            "Use Aurora Serverless v2 for variable workloads",
            "Use Reserved Instances for predictable workloads",
            "Monitor and right-size reader instances",
            "Use Aurora I/O-Optimized instances for I/O-intensive workloads",
            "Enable Aurora auto-pause for Serverless (when available)",
        ],
        "typical_monthly_cost_usd": {
            "small": 25.0,
            "medium": 200.0,
            "large": 1000.0,
        },
        "comparable_services": ["rds", "dynamodb", "redshift"],
    },
    "redshift": {
        "full_name": "Amazon Redshift",
        "category": "analytics",
        "description": "Fast, powerful, fully managed data warehouse service in the cloud.",
        "best_for": [
            "Data warehousing and analytics",
            "Business intelligence dashboards",
            "Large-scale data aggregation",
            "Historical data analysis",
            "ETL/ELT workloads",
        ],
        "not_suitable_for": [
            "Transactional workloads (use RDS or Aurora)",
            "Real-time key-value lookups",
            "Small datasets (< 100GB)",
            "Simple queries on small data",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Cluster hours (varies by node type)",
            "Storage (compressed)",
            "Redshift Spectrum (per TB scanned)",
            "Data transfer out",
            "Backup storage beyond free tier",
        ],
        "cost_optimization_tips": [
            "Use Reserved Nodes for predictable workloads (saves up to 75%)",
            "Enable concurrency scaling only when needed",
            "Use Redshift Spectrum for infrequent queries on S3 data",
            "Monitor query performance and optimize table design",
            "Use auto-pause for development clusters",
            "Compress data and use appropriate distribution keys",
        ],
        "typical_monthly_cost_usd": {
            "small": 25.0,
            "medium": 500.0,
            "large": 5000.0,
        },
        "comparable_services": ["athena", "synapse", "bigquery"],
    },
    "opensearch": {
        "full_name": "Amazon OpenSearch Service",
        "category": "analytics",
        "description": "Managed service for OpenSearch and legacy Elasticsearch, providing search, analytics, and visualization.",
        "best_for": [
            "Full-text search",
            "Log and event data analytics",
            "Application monitoring and observability",
            "E-commerce product search",
            "Security analytics",
        ],
        "not_suitable_for": [
            "Transactional workloads",
            "Simple key-value lookups",
            "Real-time analytics on streaming data",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Instance hours (varies by instance type)",
            "Storage (EBS volumes)",
            "Data transfer out",
            "UltraWarm storage (for older data)",
        ],
        "cost_optimization_tips": [
            "Use UltraWarm nodes for older, less frequently accessed data",
            "Use Reserved Instances for predictable workloads",
            "Right-size instances based on cluster metrics",
            "Enable automated snapshots for backup (cheaper than manual)",
            "Use index lifecycle management to move data to cold storage",
        ],
        "typical_monthly_cost_usd": {
            "small": 20.0,
            "medium": 150.0,
            "large": 800.0,
        },
        "comparable_services": ["elasticsearch", "opensearch", "algolia"],
    },
    "msk": {
        "full_name": "Amazon Managed Streaming for Apache Kafka",
        "category": "analytics",
        "description": "Fully managed Apache Kafka service for building real-time streaming applications.",
        "best_for": [
            "Real-time data pipelines",
            "Event sourcing architectures",
            "Stream processing applications",
            "Microservices communication",
            "Log aggregation",
        ],
        "not_suitable_for": [
            "Simple message queuing (use SQS)",
            "Pub/sub patterns (use SNS)",
            "Small-scale applications",
            "Non-Kafka workloads",
        ],
        "pricing_model": "provisioned",
        "cost_drivers": [
            "Broker hours (varies by instance type)",
            "Storage (per GB-month)",
            "Data transfer out",
            "MSK Serverless (per provisioned capacity unit)",
        ],
        "cost_optimization_tips": [
            "Use MSK Serverless for unpredictable workloads",
            "Right-size broker instances based on throughput",
            "Monitor partition count and adjust appropriately",
            "Use compression to reduce storage and transfer costs",
            "Enable multi-AZ only for production workloads",
        ],
        "typical_monthly_cost_usd": {
            "small": 50.0,
            "medium": 300.0,
            "large": 1500.0,
        },
        "comparable_services": ["kinesis", "sqs", "eventbridge"],
    },
}


# Service aliases for flexible lookups
SERVICE_ALIASES: dict[str, str] = {
    "s3": "s3",
    "simple storage service": "s3",
    "storage": "s3",
    "dynamodb": "dynamodb",
    "dynamo db": "dynamodb",
    "ddb": "dynamodb",
    "rds": "rds",
    "relational database": "rds",
    "mysql": "rds",
    "postgresql": "rds",
    "elasticache": "elasticache",
    "elastic cache": "elasticache",
    "redis": "elasticache",
    "memcached": "elasticache",
    "cache": "elasticache",
    "lambda": "lambda",
    "serverless": "lambda",
    "function": "lambda",
    "ec2": "ec2",
    "elastic compute": "ec2",
    "virtual machine": "ec2",
    "ecs": "ecs",
    "elastic container service": "ecs",
    "fargate": "ecs",
    "container": "ecs",
    "sqs": "sqs",
    "queue": "sqs",
    "message queue": "sqs",
    "sns": "sns",
    "notification": "sns",
    "pubsub": "sns",
    "pub/sub": "sns",
    "kinesis": "kinesis",
    "streaming": "kinesis",
    "data stream": "kinesis",
    "api gateway": "api_gateway",
    "api": "api_gateway",
    "rest api": "api_gateway",
    "cloudfront": "cloudfront",
    "cdn": "cloudfront",
    "aurora": "aurora",
    "redshift": "redshift",
    "data warehouse": "redshift",
    "warehouse": "redshift",
    "opensearch": "opensearch",
    "elasticsearch": "opensearch",
    "search": "opensearch",
    "msk": "msk",
    "kafka": "msk",
    "managed kafka": "msk",
}


def get_service_info(service_name: str) -> dict:
    """
    Look up service information from the catalog.
    
    Args:
        service_name: Service name or alias (case-insensitive)
    
    Returns:
        Service catalog entry or a not_found dict with suggestions
    """
    # Normalize input
    normalized = service_name.lower().strip()
    
    # Check aliases
    if normalized in SERVICE_ALIASES:
        normalized = SERVICE_ALIASES[normalized]
    
    # Look up in catalog
    if normalized in AWS_SERVICE_CATALOG:
        return AWS_SERVICE_CATALOG[normalized]
    
    # Find similar services
    similar = []
    for key in AWS_SERVICE_CATALOG:
        if normalized in key or key in normalized:
            similar.append(key)
    
    return {
        "not_found": True,
        "queried_service": service_name,
        "similar_services": similar[:5] if similar else list(AWS_SERVICE_CATALOG.keys())[:5],
        "message": f"Service '{service_name}' not found in catalog. Did you mean one of these?",
    }


def compare_services(use_case: str) -> dict:
    """
    Find the best AWS services for a given use case.
    
    Args:
        use_case: Natural language description of the use case
    
    Returns:
        Dict with matched services and recommendations
    """
    use_case_lower = use_case.lower()
    
    # Tokenize use case for matching
    use_case_tokens = set(use_case_lower.split())
    
    matches = []
    
    for service_key, service_info in AWS_SERVICE_CATALOG.items():
        score = 0
        
        # Check best_for matches
        for best_for in service_info.get("best_for", []):
            best_for_lower = best_for.lower()
            # Check for token overlap
            best_for_tokens = set(best_for_lower.split())
            overlap = use_case_tokens & best_for_tokens
            score += len(overlap) * 2
            
            # Check for substring match
            if use_case_lower in best_for_lower or best_for_lower in use_case_lower:
                score += 10
            
            # Check for keyword matches
            for token in use_case_tokens:
                if len(token) > 3 and token in best_for_lower:
                    score += 3
        
        # Check category match
        if service_info.get("category", "").lower() in use_case_lower:
            score += 5
        
        # Check description match
        description = service_info.get("description", "").lower()
        if use_case_lower in description:
            score += 8
        
        if score > 0:
            match_entry = dict(service_info)
            match_entry["service_key"] = service_key
            match_entry["score"] = score
            
            # Add recommendation based on cost efficiency
            if score >= 5:
                tips = service_info.get("cost_optimization_tips", [])
                if tips:
                    match_entry["recommendation"] = (
                        f"For cost-efficient {service_info['full_name']} usage: {tips[0]}"
                    )
                else:
                    match_entry["recommendation"] = (
                        f"{service_info['full_name']} is a good fit for this use case."
                    )
            
            matches.append(match_entry)
    
    # Sort by score and take top 3
    matches.sort(key=lambda x: x["score"], reverse=True)
    top_matches = matches[:3]
    
    # Add recommendation for the best match
    if top_matches:
        best = top_matches[0]
        if "recommendation" not in best:
            best["recommendation"] = (
                f"Based on your use case, {best['full_name']} appears to be the best fit. "
                f"Consider the cost optimization tips: {', '.join(best.get('cost_optimization_tips', [])[:2])}"
            )
    
    return {
        "use_case": use_case,
        "matches": top_matches,
    }


def estimate_cost(service_name: str, usage: dict) -> dict:
    """
    Estimate monthly cost for a service based on usage parameters.
    
    Args:
        service_name: AWS service name
        usage: Dict with usage parameters like:
            - requests_per_month
            - storage_gb
            - read_units_per_sec
            - write_units_per_sec
            - compute_hours
            - data_transfer_gb
    
    Returns:
        Dict with estimated cost and breakdown
    """
    # Normalize service name
    normalized = service_name.lower().strip()
    if normalized in SERVICE_ALIASES:
        normalized = SERVICE_ALIASES[normalized]
    
    service_info = AWS_SERVICE_CATALOG.get(normalized)
    if not service_info:
        return {
            "error": True,
            "message": f"Unknown service: {service_name}",
            "disclaimer": "Estimate only. Check AWS Pricing Calculator for accuracy.",
        }
    
    breakdown = {}
    total = 0.0
    
    # Pricing formulas (simplified, approximate AWS pricing)
    if normalized == "s3":
        storage_gb = usage.get("storage_gb", 0)
        requests = usage.get("requests_per_month", 0)
        
        storage_cost = storage_gb * 0.023  # Standard tier
        request_cost = (requests / 1000) * 0.0004  # GET requests
        
        breakdown = {
            "storage": round(storage_cost, 4),
            "requests": round(request_cost, 4),
        }
        total = storage_cost + request_cost
    
    elif normalized == "dynamodb":
        read_units = usage.get("read_units_per_sec", 0)
        write_units = usage.get("write_units_per_sec", 0)
        storage_gb = usage.get("storage_gb", 0)
        
        # On-demand pricing (per million requests)
        read_cost = (read_units * 0.00013) * 730  # per hour * hours/month
        write_cost = (write_units * 0.00065) * 730
        storage_cost = storage_gb * 0.25
        
        breakdown = {
            "read_requests": round(read_cost, 4),
            "write_requests": round(write_cost, 4),
            "storage": round(storage_cost, 4),
        }
        total = read_cost + write_cost + storage_cost
    
    elif normalized == "lambda":
        requests = usage.get("requests_per_month", 0)
        compute_hours = usage.get("compute_hours", 0)
        
        request_cost = requests * 0.0000002  # $0.20 per million
        compute_cost = compute_hours * 3600 * 0.0000166667  # per GB-second
        
        breakdown = {
            "invocations": round(request_cost, 4),
            "compute_duration": round(compute_cost, 4),
        }
        total = request_cost + compute_cost
    
    elif normalized == "rds" or normalized == "aurora":
        compute_hours = usage.get("compute_hours", 0)
        storage_gb = usage.get("storage_gb", 0)
        
        # t3.medium pricing
        compute_cost = compute_hours * 0.068
        storage_cost = storage_gb * 0.115  # gp3
        
        breakdown = {
            "compute": round(compute_cost, 4),
            "storage": round(storage_cost, 4),
        }
        total = compute_cost + storage_cost
    
    elif normalized == "elasticache":
        compute_hours = usage.get("compute_hours", 0)
        
        # cache.t3.micro pricing
        compute_cost = compute_hours * 0.017
        
        breakdown = {
            "compute": round(compute_cost, 4),
        }
        total = compute_cost
    
    elif normalized == "sqs":
        requests = usage.get("requests_per_month", 0)
        
        request_cost = requests * 0.0000004  # $0.40 per million
        
        breakdown = {
            "requests": round(request_cost, 4),
        }
        total = request_cost
    
    elif normalized == "ec2":
        compute_hours = usage.get("compute_hours", 0)
        storage_gb = usage.get("storage_gb", 0)
        
        # t3.medium on-demand
        compute_cost = compute_hours * 0.0416
        storage_cost = storage_gb * 0.10  # gp3
        
        breakdown = {
            "compute": round(compute_cost, 4),
            "storage": round(storage_cost, 4),
        }
        total = compute_cost + storage_cost
    
    else:
        # Generic estimate for other services
        return {
            "service": service_name,
            "estimated_monthly_cost_usd": 0,
            "breakdown": {},
            "disclaimer": f"Pricing estimates not available for {service_name}. Check AWS Pricing Calculator for accuracy.",
        }
    
    return {
        "service": service_info["full_name"],
        "service_key": normalized,
        "estimated_monthly_cost_usd": round(total, 2),
        "breakdown": breakdown,
        "disclaimer": "Estimate only. Actual costs may vary. Check AWS Pricing Calculator for accuracy.",
    }


if __name__ == "__main__":
    # Test the functions
    print("=== Service Info Test ===")
    print(json.dumps(get_service_info("s3"), indent=2))
    
    print("\n=== Compare Services Test ===")
    print(json.dumps(compare_services("session storage for web app"), indent=2))
    
    print("\n=== Cost Estimate Test ===")
    print(json.dumps(estimate_cost("dynamodb", {
        "read_units_per_sec": 100,
        "write_units_per_sec": 50,
        "storage_gb": 10,
    }), indent=2))