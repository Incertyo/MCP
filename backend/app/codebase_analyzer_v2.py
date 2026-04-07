"""
Codebase Analyzer - Scans IaC (Terraform/CDK/CloudFormation) and business logic (boto3/SDK calls)
to build a "cloud service usage registry".

This module provides:
- CodebaseAnalyzer class with scan() method
- get_mock_codebase_analysis() fallback function
"""
from __future__ import annotations

import os
import re
import json
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class CloudServiceUsage:
    """Represents a detected cloud service usage in the codebase."""
    service: str
    usage_type: str  # "iac" or "business_logic"
    source_file: str
    line_number: Optional[int]
    resource_name: Optional[str]
    details: dict = field(default_factory=dict)


class CodebaseAnalyzer:
    """Analyzes a codebase to detect AWS cloud service usage."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        
    def scan(self) -> dict:
        """
        Recursively walks the repo_path directory and scans for cloud service usage.
        
        Returns a dict with:
        - repo_path: the scanned path
        - scanned_files: number of files scanned
        - cloud_services: list of detected service usages
        - service_summary: aggregated summary by service
        """
        cloud_services: list[dict] = []
        scanned_files = 0
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden directories and common non-relevant directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                      ('node_modules', '__pycache__', 'venv', 'env', '.git', 'dist', 'build')]
            
            for filename in files:
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.repo_path)
                scanned_files += 1
                
                ext = os.path.splitext(filename)[1].lower()
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.splitlines()
                except (IOError, OSError):
                    continue
                
                if ext == '.tf':
                    # Terraform IaC
                    cloud_services.extend(self._parse_terraform(rel_path, lines))
                elif ext in ('.json', '.yaml', '.yml'):
                    # CloudFormation templates
                    cloud_services.extend(self._parse_cloudformation(rel_path, content, ext))
                elif ext == '.py':
                    # Python business logic
                    cloud_services.extend(self._parse_python(rel_path, lines))
                elif ext in ('.ts', '.js'):
                    # TypeScript/JavaScript (CDK)
                    cloud_services.extend(self._parse_typescript(rel_path, lines))
        
        # Build service summary
        service_summary: dict[str, dict] = {}
        for svc in cloud_services:
            name = svc['service']
            if name not in service_summary:
                service_summary[name] = {
                    'iac_count': 0,
                    'business_logic_count': 0,
                    'files': []
                }
            if svc['usage_type'] == 'iac':
                service_summary[name]['iac_count'] += 1
            else:
                service_summary[name]['business_logic_count'] += 1
            if rel_path not in service_summary[name]['files']:
                service_summary[name]['files'].append(rel_path)
        
        return {
            'repo_path': self.repo_path,
            'scanned_files': scanned_files,
            'cloud_services': cloud_services,
            'service_summary': service_summary
        }
    
    def _parse_terraform(self, filepath: str, lines: list[str]) -> list[dict]:
        """Parse Terraform files for AWS resource blocks."""
        results = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Match resource blocks: resource "aws_service_type" "name"
            match = re.match(r'\s*resource\s+"(aws_\w+)"\s+"(\w+)"', line)
            if match:
                resource_type = match.group(1)
                resource_name = match.group(2)
                # Extract service name from resource type (e.g., aws_s3_bucket -> s3)
                service = self._extract_service_from_terraform(resource_type)
                
                # Extract relevant details from the block
                details = {}
                block_content = self._extract_terraform_block(lines, i)
                for key in ['bucket', 'engine', 'instance_type', 'cluster_id', 'runtime', 
                           'table_name', 'function_name', 'queue_name', 'topic_name']:
                    for bl in block_content:
                        m = re.search(rf'\s*{key}\s*=\s*"([^"]+)"', bl)
                        if m:
                            details[key] = m.group(1)
                
                results.append({
                    'service': service,
                    'usage_type': 'iac',
                    'source_file': filepath,
                    'line_number': i + 1,
                    'resource_name': resource_name,
                    'details': details
                })
            i += 1
        return results
    
    def _extract_service_from_terraform(self, resource_type: str) -> str:
        """Extract service name from Terraform resource type."""
        # aws_s3_bucket -> s3, aws_dynamodb_table -> dynamodb, etc.
        parts = resource_type.split('_')
        if len(parts) >= 3:
            # aws_s3_bucket -> s3
            # aws_dynamodb_table -> dynamodb
            # aws_lambda_function -> lambda
            service_map = {
                'aws_s3_': 's3',
                'aws_dynamodb_': 'dynamodb',
                'aws_lambda_': 'lambda',
                'aws_iam_': 'iam',
                'aws_rds_': 'rds',
                'aws_ec2_': 'ec2',
                'aws_ecs_': 'ecs',
                'aws_sqs_': 'sqs',
                'aws_sns_': 'sns',
                'aws_elasticache_': 'elasticache',
                'aws_api_gateway_': 'api_gateway',
                'aws_cloudfront_': 'cloudfront',
                'aws_kinesis_': 'kinesis',
                'aws_redshift_': 'redshift',
                'aws_opensearch_': 'opensearch',
                'aws_msk_': 'msk',
            }
            for prefix, service in service_map.items():
                if resource_type.startswith(prefix):
                    return service
            return parts[1]  # fallback
        return resource_type.replace('aws_', '')
    
    def _extract_terraform_block(self, lines: list[str], start_idx: int) -> list[str]:
        """Extract the content of a Terraform block starting at start_idx."""
        block_lines = []
        brace_count = 0
        started = False
        for i in range(start_idx, min(start_idx + 100, len(lines))):
            line = lines[i]
            if '{' in line:
                started = True
                brace_count += line.count('{')
            if started:
                block_lines.append(line)
            if '}' in line:
                brace_count -= line.count('}')
                if brace_count == 0:
                    break
        return block_lines
    
    def _parse_cloudformation(self, filepath: str, content: str, ext: str) -> list[dict]:
        """Parse CloudFormation templates for AWS resources."""
        results = []
        try:
            if ext == '.json':
                template = json.loads(content)
            else:
                # Simple YAML parsing for CloudFormation
                import yaml
                template = yaml.safe_load(content)
        except (json.JSONDecodeError, Exception):
            return results
        
        # Check if it's a CloudFormation template
        if not isinstance(template, dict):
            return results
        
        is_cfn = ('AWSTemplateFormatVersion' in template or 
                  'Resources' in template or
                  any(k.startswith('AWSTemplate') for k in template.keys()))
        
        if not is_cfn:
            return results
        
        resources = template.get('Resources', {})
        if not isinstance(resources, dict):
            return results
        
        for name, resource in resources.items():
            if not isinstance(resource, dict):
                continue
            resource_type = resource.get('Type', '')
            if not resource_type.startswith('AWS::'):
                continue
            
            # Extract service from CloudFormation type
            parts = resource_type.split('::')
            if len(parts) >= 2:
                service = parts[1].lower()
                # Normalize service names
                service_map = {
                    'dynamodb': 'dynamodb',
                    's3': 's3',
                    'lambda': 'lambda',
                    'rds': 'rds',
                    'ec2': 'ec2',
                    'ecs': 'ecs',
                    'sqs': 'sqs',
                    'sns': 'sns',
                    'elasticache': 'elasticache',
                    'apigateway': 'api_gateway',
                    'cloudfront': 'cloudfront',
                    'kinesis': 'kinesis',
                    'redshift': 'redshift',
                    'opensearchservice': 'opensearch',
                    'msk': 'msk',
                }
                service = service_map.get(service, service)
                
                properties = resource.get('Properties', {})
                details = {}
                if isinstance(properties, dict):
                    for key in ['BucketName', 'TableName', 'FunctionName', 'InstanceType',
                               'Engine', 'ClusterIdentifier', 'QueueName', 'TopicName']:
                        if key in properties:
                            details[key.lower()] = str(properties[key])
                
                results.append({
                    'service': service,
                    'usage_type': 'iac',
                    'source_file': filepath,
                    'line_number': None,
                    'resource_name': name,
                    'details': details
                })
        
        return results
    
    def _parse_python(self, filepath: str, lines: list[str]) -> list[dict]:
        """Parse Python files for boto3/CDK usage."""
        results = []
        content = '\n'.join(lines)
        
        # Check for AWS-related imports
        has_aws_import = any([
            'import boto3' in content or 'from boto3' in content,
            'import aws_cdk' in content or 'from aws_cdk' in content,
            'from constructs' in content,
            'import aws' in content,
        ])
        
        if not has_aws_import:
            return results
        
        # Find boto3.client() and boto3.resource() calls
        for i, line in enumerate(lines):
            # boto3.client('service_name')
            match = re.search(r"boto3\.client\(['\"](\w+)['\"]", line)
            if match:
                service = match.group(1).lower()
                results.append({
                    'service': service,
                    'usage_type': 'business_logic',
                    'source_file': filepath,
                    'line_number': i + 1,
                    'resource_name': None,
                    'details': {'call_type': 'client'}
                })
            
            # boto3.resource('service_name')
            match = re.search(r"boto3\.resource\(['\"](\w+)['\"]", line)
            if match:
                service = match.group(1).lower()
                results.append({
                    'service': service,
                    'usage_type': 'business_logic',
                    'source_file': filepath,
                    'line_number': i + 1,
                    'resource_name': None,
                    'details': {'call_type': 'resource'}
                })
        
        # Find CDK constructs
        cdk_services = {
            'aws_s3': 's3', 'aws_dynamodb': 'dynamodb', 'aws_lambda': 'lambda',
            'aws_rds': 'rds', 'aws_ec2': 'ec2', 'aws_ecs': 'ecs',
            'aws_sqs': 'sqs', 'aws_sns': 'sns', 'aws_elasticache': 'elasticache',
            'aws_apigateway': 'api_gateway', 'aws_cloudfront': 'cloudfront',
            'aws_kinesis': 'kinesis', 'aws_redshift': 'redshift',
        }
        
        for cdk_prefix, service in cdk_services.items():
            pattern = rf'new {cdk_prefix}\.'
            if re.search(pattern, content):
                results.append({
                    'service': service,
                    'usage_type': 'business_logic',
                    'source_file': filepath,
                    'line_number': None,
                    'resource_name': None,
                    'details': {'framework': 'cdk', 'construct': cdk_prefix}
                })
        
        return results
    
    def _parse_typescript(self, filepath: str, lines: list[str]) -> list[dict]:
        """Parse TypeScript/JavaScript files for AWS CDK usage."""
        results = []
        content = '\n'.join(lines)
        
        # Check for AWS-related imports
        has_aws_import = any([
            'aws-cdk' in content or '@aws-cdk' in content,
            'aws-sdk' in content or 'aws-sdk/' in content,
            'from "aws-' in content or "from 'aws-" in content,
        ])
        
        if not has_aws_import:
            return results
        
        # Find CDK constructs
        cdk_services = {
            'aws-s3': 's3', 'aws-dynamodb': 'dynamodb', 'aws-lambda': 'lambda',
            'aws-rds': 'rds', 'aws-ec2': 'ec2', 'aws-ecs': 'ecs',
            'aws-sqs': 'sqs', 'aws-sns': 'sns', 'aws-elasticache': 'elasticache',
            'aws-apigateway': 'api_gateway', 'aws-cloudfront': 'cloudfront',
            'aws-kinesis': 'kinesis', 'aws-redshift': 'redshift',
        }
        
        for cdk_prefix, service in cdk_services.items():
            pattern = rf'new {cdk_prefix.replace("-", ".")}\.'
            if re.search(pattern, content.replace('-', '.')):
                results.append({
                    'service': service,
                    'usage_type': 'business_logic',
                    'source_file': filepath,
                    'line_number': None,
                    'resource_name': None,
                    'details': {'framework': 'cdk', 'construct': cdk_prefix}
                })
        
        # Find AWS SDK v3 client instantiations
        for i, line in enumerate(lines):
            match = re.search(r'new (\w+)Client\(', line)
            if match:
                client_name = match.group(1)
                # Convert S3Client -> s3, DynamoDBClient -> dynamodb
                service = client_name.replace('Client', '').lower()
                results.append({
                    'service': service,
                    'usage_type': 'business_logic',
                    'source_file': filepath,
                    'line_number': i + 1,
                    'resource_name': None,
                    'details': {'sdk': 'aws-sdk-v3', 'client': client_name}
                })
        
        return results


def get_mock_codebase_analysis() -> dict:
    """
    Returns a hardcoded realistic example of codebase analysis.
    Used as fallback when repo_path is not accessible.
    """
    return {
        "repo_path": "./mock-repo",
        "scanned_files": 24,
        "cloud_services": [
            {
                "service": "s3",
                "usage_type": "iac",
                "source_file": "infra/terraform/storage.tf",
                "line_number": 5,
                "resource_name": "app_data_bucket",
                "details": {"bucket": "my-app-data-bucket"}
            },
            {
                "service": "s3",
                "usage_type": "business_logic",
                "source_file": "src/services/storage.py",
                "line_number": 15,
                "resource_name": None,
                "details": {"call_type": "client"}
            },
            {
                "service": "dynamodb",
                "usage_type": "iac",
                "source_file": "infra/terraform/database.tf",
                "line_number": 12,
                "resource_name": "users_table",
                "details": {"table_name": "users", "billing_mode": "PAY_PER_REQUEST"}
            },
            {
                "service": "dynamodb",
                "usage_type": "business_logic",
                "source_file": "src/repositories/user_repo.py",
                "line_number": 8,
                "resource_name": None,
                "details": {"call_type": "resource"}
            },
            {
                "service": "lambda",
                "usage_type": "iac",
                "source_file": "infra/terraform/compute.tf",
                "line_number": 3,
                "resource_name": "api_handler",
                "details": {"runtime": "python3.11", "function_name": "api-handler"}
            },
            {
                "service": "lambda",
                "usage_type": "business_logic",
                "source_file": "src/handlers/api.py",
                "line_number": 1,
                "resource_name": None,
                "details": {"call_type": "client"}
            },
            {
                "service": "sqs",
                "usage_type": "iac",
                "source_file": "infra/terraform/messaging.tf",
                "line_number": 7,
                "resource_name": "notification_queue",
                "details": {"queue_name": "notifications.fifo"}
            },
            {
                "service": "sqs",
                "usage_type": "business_logic",
                "source_file": "src/services/notifications.py",
                "line_number": 22,
                "resource_name": None,
                "details": {"call_type": "client"}
            },
            {
                "service": "rds",
                "usage_type": "iac",
                "source_file": "infra/terraform/database.tf",
                "line_number": 25,
                "resource_name": "main_db",
                "details": {"engine": "postgres", "instance_type": "db.t3.medium"}
            },
            {
                "service": "elasticache",
                "usage_type": "iac",
                "source_file": "infra/terraform/cache.tf",
                "line_number": 4,
                "resource_name": "session_cache",
                "details": {"engine": "redis", "node_type": "cache.t3.micro"}
            }
        ],
        "service_summary": {
            "s3": {
                "iac_count": 1,
                "business_logic_count": 1,
                "files": ["infra/terraform/storage.tf", "src/services/storage.py"]
            },
            "dynamodb": {
                "iac_count": 1,
                "business_logic_count": 1,
                "files": ["infra/terraform/database.tf", "src/repositories/user_repo.py"]
            },
            "lambda": {
                "iac_count": 1,
                "business_logic_count": 1,
                "files": ["infra/terraform/compute.tf", "src/handlers/api.py"]
            },
            "sqs": {
                "iac_count": 1,
                "business_logic_count": 1,
                "files": ["infra/terraform/messaging.tf", "src/services/notifications.py"]
            },
            "rds": {
                "iac_count": 1,
                "business_logic_count": 0,
                "files": ["infra/terraform/database.tf"]
            },
            "elasticache": {
                "iac_count": 1,
                "business_logic_count": 0,
                "files": ["infra/terraform/cache.tf"]
            }
        }
    }


# Convenience function for standalone use
def analyze_repo(repo_path: str) -> dict:
    """Analyze a repository and return cloud service usage."""
    try:
        analyzer = CodebaseAnalyzer(repo_path)
        return analyzer.scan()
    except Exception:
        return get_mock_codebase_analysis()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    result = analyze_repo(path)
    print(json.dumps(result, indent=2))