from __future__ import annotations

from datetime import datetime
from typing import Any

from .datadog import telemetry
from .models import AccountInput, AccountProfile, AppState, ChatMessage, ChatResponse, DashboardResponse, EventItem, ObservabilitySummary, Recommendation, RecommendationStatus, ResourceState
from .services import PrismService


class PrismDomainAdapter:
    def __init__(self, service: PrismService) -> None:
        self.service = service

    def get_state(self) -> AppState:
        return self.service.get_state()

    def get_account(self) -> AccountProfile | None:
        return self.service.get_account()

    def onboard_account(self, payload: AccountInput) -> AccountProfile:
        return self.service.onboard_account(payload)

    def get_dashboard(self) -> DashboardResponse:
        return self.service.get_dashboard()

    def list_recommendations(self, status: RecommendationStatus | None = None) -> list[Recommendation]:
        recommendations = self.service.list_recommendations()
        if status is None:
            return recommendations
        return [item for item in recommendations if item.status == status]

    def get_recommendation(self, recommendation_id: str) -> Recommendation:
        recommendation = next((item for item in self.service.list_recommendations() if item.id == recommendation_id), None)
        if recommendation is None:
            raise KeyError(recommendation_id)
        return recommendation

    def accept_recommendation(self, recommendation_id: str) -> Recommendation:
        return self.service.update_recommendation(recommendation_id, "accepted")

    def reject_recommendation(self, recommendation_id: str) -> Recommendation:
        return self.service.update_recommendation(recommendation_id, "rejected")

    def recur_recommendation(self, recommendation_id: str) -> Recommendation:
        return self.service.recur_recommendation(recommendation_id)

    def list_events(self) -> list[EventItem]:
        return sorted(self.service.get_events(), key=lambda item: item.created_at, reverse=True)

    def clear_events(self) -> dict[str, str]:
        return self.service.clear_events()

    def get_observability(self) -> ObservabilitySummary:
        return telemetry.summary()

    def clear_observability(self) -> dict[str, str]:
        return self.service.clear_observability()

    def get_chat_history(self) -> list[ChatMessage]:
        return self.service.get_chat_history()

    def clear_chat_history(self) -> dict[str, str]:
        return self.service.clear_chat_history()

    def send_chat_message(self, message: str) -> ChatResponse:
        return self.service.chat(message)

    def suggest_next_action(self) -> dict[str, Any]:
        state = self.get_state()
        if not state.account:
            return {
                "summary": "Link an AWS account first so Prism can evaluate seeded resources, costs, and recommendations.",
                "recommendation": None,
                "resource": None,
            }

        open_recommendation = next((item for item in state.recommendations if item.status == "open"), None)
        if open_recommendation is None:
            return {
                "summary": "All current seeded recommendations are resolved. The environment is already in its simulated optimized state.",
                "recommendation": None,
                "resource": None,
            }

        resource = next((item for item in state.resources if item.id == open_recommendation.target_resource_id), None)
        if resource is None:
            return {
                "summary": f"The next best action is {open_recommendation.title}.",
                "recommendation": open_recommendation,
                "resource": None,
            }

        return {
            "summary": (
                f"The next best action is {open_recommendation.title} on {resource.name}. "
                f"It is marked {open_recommendation.severity} severity, could save ${open_recommendation.projected_savings:.2f} per month, "
                f"and targets a resource currently costing ${resource.monthly_cost:.2f} with {resource.utilization}% utilization."
            ),
            "recommendation": open_recommendation,
            "resource": resource,
        }

    @staticmethod
    def to_python(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [PrismDomainAdapter.to_python(item) for item in value]
        if isinstance(value, dict):
            return {key: PrismDomainAdapter.to_python(item) for key, item in value.items()}
        if isinstance(value, datetime):
            return value.isoformat()
        return value
