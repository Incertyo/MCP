from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import AccountInput, AccountProfile, EventItem, Recommendation, ResourceState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_account_profile(payload: AccountInput, identity: dict[str, Any] | None = None) -> AccountProfile:
    now = utcnow()
    return AccountProfile(
        student_name=payload.student_name,
        email=payload.email,
        aws_account_id=payload.aws_account_id,
        region=payload.region,
        institution=payload.institution,
        connection_mode=payload.connection_mode,
        access_key_id_last4=(payload.access_key_id[-4:] if payload.connection_mode == "real" and payload.access_key_id else None),
        validated_arn=identity.get("arn") if identity else None,
        validated_user_id=identity.get("user_id") if identity else None,
        created_at=now,
        updated_at=now,
    )


def build_seed_resources(region: str) -> list[ResourceState]:
    return [
        ResourceState(id="ec2-1", service="EC2", name="student-web-node", region=region, monthly_cost=52.0, utilization=24, health_score=71, alerts=3, status="Running"),
        ResourceState(id="rds-1", service="RDS", name="prism-course-db", region=region, monthly_cost=84.0, utilization=38, health_score=66, alerts=4, status="Available"),
        ResourceState(id="s3-1", service="S3", name="project-artifacts", region=region, monthly_cost=18.5, utilization=61, health_score=89, alerts=1, status="Active"),
        ResourceState(id="lambda-1", service="Lambda", name="usage-analyzer", region=region, monthly_cost=12.0, utilization=57, health_score=92, alerts=0, status="Healthy"),
    ]


def seed_events(account: AccountProfile) -> list[EventItem]:
    return [
        EventItem(
            id="evt-account-linked",
            type="account",
            title="AWS account linked",
            description=f"{account.connection_mode.title()} onboarding completed for {account.student_name}.",
            created_at=utcnow(),
        )
    ]


def build_recommendations() -> list[Recommendation]:
    raw = [
        {
            "id": "rec-ec2-rightsize",
            "title": "Right-size underutilized EC2 node",
            "service": "EC2",
            "severity": "high",
            "target_resource_id": "ec2-1",
            "rationale": "The web node is consistently below 30% utilization while generating repeated cost alerts.",
            "projected_savings": 22.0,
            "impact": {"monthly_cost_delta": -22.0, "utilization_delta": 18, "health_score_delta": 11, "alerts_delta": -2, "summary": "Move to a smaller instance size and tighten auto-scaling thresholds."},
        },
        {
            "id": "rec-rds-storage",
            "title": "Enable storage auto-scaling and reserve capacity",
            "service": "RDS",
            "severity": "high",
            "target_resource_id": "rds-1",
            "rationale": "The database has headroom for a cheaper reservation profile and reduced burst pressure.",
            "projected_savings": 28.0,
            "impact": {"monthly_cost_delta": -28.0, "utilization_delta": 9, "health_score_delta": 13, "alerts_delta": -2, "summary": "Shift to a reserved profile with auto-scaling to stabilize latency spikes."},
        },
        {
            "id": "rec-s3-lifecycle",
            "title": "Apply S3 lifecycle rules for archival",
            "service": "S3",
            "severity": "medium",
            "target_resource_id": "s3-1",
            "rationale": "Old build artifacts are staying in the standard tier longer than necessary.",
            "projected_savings": 6.5,
            "impact": {"monthly_cost_delta": -6.5, "utilization_delta": 4, "health_score_delta": 5, "alerts_delta": -1, "summary": "Archive inactive objects after 30 days and expire temporary uploads."},
        },
    ]
    return [Recommendation(**item) for item in raw]
