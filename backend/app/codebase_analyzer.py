"""
Parses uploaded codebase (IaC: Terraform/CloudFormation, and business logic: Python/Node/Java)
to detect which AWS services are used and how (read/write patterns, API calls, resource names).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any

AWS_SERVICE_PATTERNS: dict[str, dict[str, Any]] = {
    "DynamoDB": {
        "iac_keywords": ["aws_dynamodb_table", "AWS::DynamoDB::Table", "dynamodb"],
        "code_keywords": ["dynamodb", "DynamoDB", "put_item", "get_item", "query", "scan",
                          "update_item", "delete_item", "batch_write", "batch_get"],
        "read_ops": ["get_item", "query", "scan", "batch_get_item"],
        "write_ops": ["put_item", "update_item", "delete_item", "batch_write_item"],
    },
    "S3": {
        "iac_keywords": ["aws_s3_bucket", "AWS::S3::Bucket", "s3"],
        "code_keywords": ["s3", "S3", "get_object", "put_object", "delete_object",
                          "list_objects", "upload_file", "download_file"],
        "read_ops": ["get_object", "list_objects", "head_object", "download_file"],
        "write_ops": ["put_object", "delete_object", "upload_file", "copy_object"],
    },
    "Lambda": {
        "iac_keywords": ["aws_lambda_function", "AWS::Lambda::Function", "lambda"],
        "code_keywords": ["lambda_client", "invoke", "Lambda", "FunctionName"],
        "read_ops": ["get_function", "list_functions"],
        "write_ops": ["invoke", "update_function_code", "create_function"],
    },
    "APIGateway": {
        "iac_keywords": ["aws_api_gateway", "AWS::ApiGateway", "apigateway"],
        "code_keywords": ["apigateway", "RestApi", "HttpApi", "stage"],
        "read_ops": [],
        "write_ops": ["create_deployment", "update_stage"],
    },
    "CosmosDB": {
        "iac_keywords": ["azurerm_cosmosdb", "cosmosdb"],
        "code_keywords": ["CosmosClient", "cosmos", "container.upsert_item",
                          "container.read_item", "container.query_items"],
        "read_ops": ["read_item", "query_items"],
        "write_ops": ["upsert_item", "delete_item", "create_item"],
    },
    "SQS": {
        "iac_keywords": ["aws_sqs_queue", "AWS::SQS::Queue"],
        "code_keywords": ["sqs", "SQS", "send_message", "receive_message", "delete_message"],
        "read_ops": ["receive_message", "get_queue_attributes"],
        "write_ops": ["send_message", "delete_message", "send_message_batch"],
    },
    "SNS": {
        "iac_keywords": ["aws_sns_topic", "AWS::SNS::Topic"],
        "code_keywords": ["sns", "SNS", "publish", "subscribe"],
        "read_ops": ["list_subscriptions"],
        "write_ops": ["publish", "subscribe", "unsubscribe"],
    },
    "ElastiCache": {
        "iac_keywords": ["aws_elasticache", "AWS::ElastiCache"],
        "code_keywords": ["redis", "memcached", "elasticache", "Redis"],
        "read_ops": ["get", "hget", "lrange"],
        "write_ops": ["set", "hset", "lpush", "expire"],
    },
    "RDS": {
        "iac_keywords": ["aws_db_instance", "AWS::RDS::DBInstance"],
        "code_keywords": ["rds", "RDS", "psycopg2", "pymysql", "sqlalchemy"],
        "read_ops": ["SELECT", "execute"],
        "write_ops": ["INSERT", "UPDATE", "DELETE"],
    },
}

@dataclass
class AwsServiceUsage:
    name: str
    operations_detected: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    buckets: list[str] = field(default_factory=list)
    throughput_mode: str | None = None
    code_references: list[str] = field(default_factory=list)
    read_operations: list[str] = field(default_factory=list)
    write_operations: list[str] = field(default_factory=list)


def analyze_codebase(files: list[dict]) -> list[AwsServiceUsage]:
    """
    files: list of {"filename": str, "content": str, "file_type": "iac"|"business_logic"}
    Returns detected AWS service usages.
    """
    usage_map: dict[str, AwsServiceUsage] = {}

    for file in files:
        filename = file.get("filename", "")
        content = file.get("content", "")
        lines = content.splitlines()

        for service_name, patterns in AWS_SERVICE_PATTERNS.items():
            all_keywords = patterns["iac_keywords"] + patterns["code_keywords"]
            matched_lines = []
            for i, line in enumerate(lines):
                for kw in all_keywords:
                    if kw.lower() in line.lower():
                        matched_lines.append(f"{filename}:{i+1} → {line.strip()[:80]}")
                        break

            if not matched_lines:
                continue

            if service_name not in usage_map:
                usage_map[service_name] = AwsServiceUsage(name=service_name)
            usage = usage_map[service_name]

            for line_ref in matched_lines:
                if line_ref not in usage.code_references:
                    usage.code_references.append(line_ref)

            for op in patterns["read_ops"]:
                if op.lower() in content.lower() and op not in usage.read_operations:
                    usage.read_operations.append(op)
                    if op not in usage.operations_detected:
                        usage.operations_detected.append(op)

            for op in patterns["write_ops"]:
                if op.lower() in content.lower() and op not in usage.write_operations:
                    usage.write_operations.append(op)
                    if op not in usage.operations_detected:
                        usage.operations_detected.append(op)

            # Extract table names (DynamoDB)
            if service_name == "DynamoDB":
                tables = re.findall(r'TableName["\s:=]+["\']?([\w-]+)', content)
                usage.tables.extend(t for t in tables if t not in usage.tables)
                if "billing_mode" in content.lower() or "PAY_PER_REQUEST" in content:
                    usage.throughput_mode = "on-demand"
                elif "PROVISIONED" in content:
                    usage.throughput_mode = "provisioned"

            # Extract bucket names (S3)
            if service_name == "S3":
                buckets = re.findall(r'Bucket["\s:=]+["\']?([\w.-]+)', content)
                usage.buckets.extend(b for b in buckets if b not in usage.buckets)

    return list(usage_map.values())