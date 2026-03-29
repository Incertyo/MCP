from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .aws_client import validate_real_account
from .datadog import telemetry
from .llm import gemini_client
from .models import AccountInput, AppState, ChatMessage, ChatResponse, DashboardKpis, DashboardResponse, EventItem, Recommendation, RecommendationStatus, ResourceState
from .repository import StateRepository
from .seed import build_account_profile, build_recommendations, build_seed_resources, seed_events


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PrismService:
    def __init__(self, repository: StateRepository) -> None:
        self.repository = repository

    def get_state(self) -> AppState:
        return self.repository.load_state()

    def get_account(self):
        return self.get_state().account

    def onboard_account(self, payload: AccountInput):
        state = self.get_state()
        identity = None
        if payload.connection_mode == "real":
            identity = validate_real_account(
                access_key_id=payload.access_key_id,
                secret_access_key=payload.secret_access_key,
                session_token=payload.session_token,
                region=payload.region,
            )
            if identity.get("account_id"):
                payload.aws_account_id = identity["account_id"]
        account = build_account_profile(payload, identity)
        state.account = account
        state.resources = build_seed_resources(payload.region)
        state.recommendations = build_recommendations()
        welcome_prefix = "validated" if payload.connection_mode == "real" else "linked"
        state.chat_messages = [
            ChatMessage(
                id="msg-welcome",
                role="assistant",
                content=f"Your AWS account is {welcome_prefix} ({payload.connection_mode} mode). I can explain optimization ideas, compare before and after impact, and guide the next best action.",
                created_at=utcnow(),
            )
        ]
        state.events = seed_events(account)
        self.repository.save_state(state)
        telemetry.increment("accounts.linked")
        telemetry.gauge("dashboard.resources", len(state.resources))
        event_text = (
            f"Real AWS account validated for {account.student_name} ({identity['arn']})."
            if identity
            else f"Mocked AWS student account linked for {account.student_name}."
        )
        telemetry.event("Account linked", event_text, tags=["source:account_onboarding", f"mode:{account.connection_mode}"])
        return account

    def get_dashboard(self) -> DashboardResponse:
        state = self.get_state()
        kpis = self._build_kpis(state.resources, state.recommendations)
        telemetry.gauge("dashboard.monthly_cost", kpis.monthly_cost)
        telemetry.gauge("dashboard.projected_savings", kpis.projected_savings)
        return DashboardResponse(
            account=state.account,
            kpis=kpis,
            resources=state.resources,
            recommendations=state.recommendations,
            events=sorted(state.events, key=lambda item: item.created_at, reverse=True),
            observability=telemetry.summary(),
        )

    def list_recommendations(self) -> list[Recommendation]:
        telemetry.increment("recommendations.list_requests")
        return self.get_state().recommendations

    def update_recommendation(self, recommendation_id: str, status: RecommendationStatus) -> Recommendation:
        state = self.get_state()
        recommendation = next((item for item in state.recommendations if item.id == recommendation_id), None)
        if recommendation is None:
            raise KeyError(recommendation_id)
        recommendation.status = status
        if status == "accepted":
            resource = next(item for item in state.resources if item.id == recommendation.target_resource_id)
            self._apply_impact(resource, recommendation)
            state.events.insert(0, EventItem(id=f"evt-{recommendation.id}", type="recommendation", title=f"{recommendation.title} accepted", description=recommendation.impact.summary, created_at=utcnow()))
            telemetry.increment("recommendations.accepted")
            telemetry.event("Recommendation accepted", f"{recommendation.title} was accepted and applied to {resource.name}.", tags=[f"recommendation:{recommendation.id}"])
        else:
            state.events.insert(0, EventItem(id=f"evt-reject-{recommendation.id}", type="recommendation", title=f"{recommendation.title} rejected", description="Recommendation was reviewed and kept open for later follow-up.", created_at=utcnow()))
            telemetry.increment("recommendations.rejected")
        self.repository.save_state(state)
        return recommendation

    def recur_recommendation(self, recommendation_id: str) -> Recommendation:
        state = self.get_state()
        if not state.account or state.account.connection_mode != "mocked":
            raise PermissionError("Recurring recommendations are only available in mocked AWS mode.")

        recommendation = next((item for item in state.recommendations if item.id == recommendation_id), None)
        if recommendation is None:
            raise KeyError(recommendation_id)

        duplicate = Recommendation.model_validate(
            {
                **recommendation.model_dump(mode="python"),
                "id": f"{recommendation.id}-recur-{uuid4().hex[:6]}",
                "title": f"Recurring {recommendation.title}",
                "status": "open",
                "projected_savings": round(recommendation.projected_savings * 0.92, 2),
                "impact": {
                    **recommendation.impact.model_dump(mode="python"),
                    "summary": f"Recurring demo scenario for {recommendation.service}. {recommendation.impact.summary}",
                },
            }
        )
        state.recommendations.insert(0, duplicate)
        state.events.insert(
            0,
            EventItem(
                id=f"evt-recur-{duplicate.id}",
                type="recommendation",
                title=f"{duplicate.title} generated",
                description="A new mock recommendation was created so the demo flow can be replayed.",
                created_at=utcnow(),
            ),
        )
        self.repository.save_state(state)
        telemetry.increment("recommendations.recurring")
        return duplicate

    def get_events(self):
        telemetry.increment("events.list_requests")
        return self.get_state().events

    def clear_events(self):
        state = self.get_state()
        state.events = []
        self.repository.save_state(state)
        telemetry.increment("events.cleared")
        return {"status": "cleared"}

    def chat(self, message: str) -> ChatResponse:
        state = self.get_state()
        user_message = ChatMessage(id=f"user-{len(state.chat_messages) + 1}", role="user", content=message, created_at=utcnow())
        fallback_text, recommendation_id, resource_id = self._reply(message, state)
        reply_text = gemini_client.generate_chat_reply(message, state, fallback_text)
        assistant_message = ChatMessage(id=f"assistant-{len(state.chat_messages) + 2}", role="assistant", content=reply_text, created_at=utcnow(), recommendation_id=recommendation_id, resource_id=resource_id)
        state.chat_messages.extend([user_message, assistant_message])
        self.repository.save_state(state)
        telemetry.increment("chat.requests")
        telemetry.increment("chat.gemini_requests" if gemini_client.enabled else "chat.rule_fallback_requests")
        return ChatResponse(reply=assistant_message, history=state.chat_messages)

    def get_chat_history(self):
        return self.get_state().chat_messages

    def clear_chat_history(self):
        state = self.get_state()
        state.chat_messages = []
        self.repository.save_state(state)
        telemetry.increment("chat.cleared")
        return {"status": "cleared"}

    def clear_observability(self):
        telemetry.clear()
        return {"status": "cleared"}

    def _build_kpis(self, resources: list[ResourceState], recommendations: list[Recommendation]) -> DashboardKpis:
        total_cost = round(sum(item.monthly_cost for item in resources), 2)
        projected = round(sum(item.projected_savings for item in recommendations if item.status == "open"), 2)
        utilization = round(sum(item.utilization for item in resources) / len(resources)) if resources else 0
        alerts = sum(item.alerts for item in resources)
        return DashboardKpis(monthly_cost=total_cost, projected_savings=projected, utilization_score=utilization, alert_count=alerts, services_covered=len({item.service for item in resources}))

    def _apply_impact(self, resource: ResourceState, recommendation: Recommendation) -> None:
        resource.monthly_cost = round(max(resource.monthly_cost + recommendation.impact.monthly_cost_delta, 0), 2)
        resource.utilization = max(0, min(resource.utilization + recommendation.impact.utilization_delta, 100))
        resource.health_score = max(0, min(resource.health_score + recommendation.impact.health_score_delta, 100))
        resource.alerts = max(resource.alerts + recommendation.impact.alerts_delta, 0)
        resource.status = "Optimized"

    def _reply(self, message: str, state: AppState) -> tuple[str, str | None, str | None]:
        lowered = message.lower()
        open_rec = next((item for item in state.recommendations if item.status == "open"), None)
        accepted = [item for item in state.recommendations if item.status == "accepted"]
        if not state.account:
            return ("Link an AWS account first (mocked demo mode or real validation mode). Once it is connected, I can explain costs, recommendations, and projected savings.", None, None)
        if "why" in lowered and open_rec:
            target = next(item for item in state.resources if item.id == open_rec.target_resource_id)
            return (f"{open_rec.title} is the top priority because {open_rec.rationale} It targets {target.name}, currently costing ${target.monthly_cost:.2f}/month with {target.utilization}% utilization and {target.alerts} alerts.", open_rec.id, target.id)
        if "compare" in lowered or "before" in lowered or "after" in lowered:
            current_cost = sum(item.monthly_cost for item in state.resources)
            accepted_savings = sum(item.projected_savings for item in accepted)
            return (f"Current monthly spend is ${current_cost:.2f}. Accepted recommendations have already realized ${accepted_savings:.2f} in simulated savings, and {sum(item.alerts for item in state.resources)} alerts remain across the stack.", accepted[0].id if accepted else open_rec.id if open_rec else None, accepted[0].target_resource_id if accepted else open_rec.target_resource_id if open_rec else None)
        if "summary" in lowered or "changes" in lowered:
            if not accepted:
                return ("No optimization has been accepted yet. The quickest win is to accept the EC2 or RDS recommendation to show a clear before and after shift in cost and health.", open_rec.id if open_rec else None, open_rec.target_resource_id if open_rec else None)
            titles = ", ".join(item.title for item in accepted)
            total = sum(item.projected_savings for item in accepted)
            return (f"Accepted changes so far: {titles}. Together they have produced ${total:.2f} in simulated monthly savings and improved service health across the affected resources.", accepted[0].id, accepted[0].target_resource_id)
        if "next" in lowered or "suggest" in lowered:
            if open_rec:
                return (f"The next best action is {open_rec.title}. It is marked {open_rec.severity} severity and would save about ${open_rec.projected_savings:.2f} per month. Accepting it will immediately update the dashboard and timeline.", open_rec.id, open_rec.target_resource_id)
            return ("All seeded recommendations are resolved. The demo stack is in an optimized state right now.", None, None)
        return ("I can explain why a recommendation exists, compare before vs after impact, summarize accepted changes, or suggest the next optimization to apply.", open_rec.id if open_rec else None, open_rec.target_resource_id if open_rec else None)
