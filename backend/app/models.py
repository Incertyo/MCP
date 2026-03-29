from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
RecommendationStatus = Literal["open", "accepted", "rejected"]
ResourceType = Literal["EC2", "RDS", "S3", "Lambda"]
ConnectionMode = Literal["mocked", "real"]


class AccountInput(BaseModel):
    student_name: str
    email: str
    aws_account_id: str = Field(min_length=6)
    connection_mode: ConnectionMode = "mocked"
    access_key_id: str = ""
    secret_access_key: str = ""
    session_token: str = ""
    region: str = "ap-south-1"
    institution: str = "Student Lab"


class AccountProfile(BaseModel):
    id: str = "primary"
    student_name: str
    email: str
    aws_account_id: str
    region: str
    institution: str
    connected: bool = True
    connection_mode: ConnectionMode = "mocked"
    access_key_id_last4: str | None = None
    validated_arn: str | None = None
    validated_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ResourceState(BaseModel):
    id: str
    service: ResourceType
    name: str
    region: str
    monthly_cost: float
    utilization: int = Field(ge=0, le=100)
    health_score: int = Field(ge=0, le=100)
    alerts: int = Field(ge=0)
    status: str


class ImpactPreview(BaseModel):
    monthly_cost_delta: float
    utilization_delta: int
    health_score_delta: int
    alerts_delta: int
    summary: str


class Recommendation(BaseModel):
    id: str
    title: str
    service: ResourceType
    severity: Severity
    rationale: str
    projected_savings: float
    status: RecommendationStatus = "open"
    target_resource_id: str
    impact: ImpactPreview


class EventItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    created_at: datetime


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    recommendation_id: str | None = None
    resource_id: str | None = None


class DashboardKpis(BaseModel):
    monthly_cost: float
    projected_savings: float
    utilization_score: int
    alert_count: int
    services_covered: int


class TelemetryMetric(BaseModel):
    name: str
    value: float
    last_updated: datetime


class ObservabilitySummary(BaseModel):
    status: str
    metrics: list[TelemetryMetric]
    recent_events: list[EventItem]


class DashboardResponse(BaseModel):
    account: AccountProfile | None
    kpis: DashboardKpis
    resources: list[ResourceState]
    recommendations: list[Recommendation]
    events: list[EventItem]
    observability: ObservabilitySummary


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: ChatMessage
    history: list[ChatMessage]


class AppState(BaseModel):
    account: AccountProfile | None = None
    resources: list[ResourceState] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    chat_messages: list[ChatMessage] = Field(default_factory=list)
    events: list[EventItem] = Field(default_factory=list)
