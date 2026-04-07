from __future__ import annotations

from typing import Callable

from .config import settings
from .domain_adapter import PrismDomainAdapter
from .llm import gemini_client
from .models import AccountInput, AgentActionResult, AgentRequest, AgentResponse, AppState, Recommendation


class PrismAgentRuntime:
    def __init__(self, adapter: PrismDomainAdapter) -> None:
        self.adapter = adapter

    def run(self, request: AgentRequest) -> AgentResponse:
        if not settings.agent_enabled:
            raise RuntimeError("The Prism agent is currently disabled.")

        state = self.adapter.get_state()
        actions: list[AgentActionResult] = []
        remaining_steps = max(settings.agent_max_steps, 1)

        if self._should_onboard_demo(request.message, state):
            remaining_steps = self._maybe_execute(
                request=request,
                remaining_steps=remaining_steps,
                actions=actions,
                tool_name="onboard_account",
                target_id="primary",
                action=lambda: self.adapter.onboard_account(self._build_demo_account_input()),
                success_summary=lambda account: (
                    f"Linked the mocked demo AWS account for {account.student_name} in {account.region} so the seeded dashboard, chat, and recommendations are available."
                ),
            )
            state = self.adapter.get_state()

        recommendation = next((item for item in state.recommendations if item.status == "open"), None)
        action_request = self._select_recommendation_action(request.message)
        if recommendation and action_request:
            tool_name = f"{action_request}_recommendation"
            operation: Callable[[str], Recommendation]
            if action_request == "accept":
                operation = self.adapter.accept_recommendation
            elif action_request == "reject":
                operation = self.adapter.reject_recommendation
            else:
                operation = self.adapter.recur_recommendation

            remaining_steps = self._maybe_execute(
                request=request,
                remaining_steps=remaining_steps,
                actions=actions,
                tool_name=tool_name,
                target_id=recommendation.id,
                action=lambda: operation(recommendation.id),
                success_summary=lambda updated: self._build_recommendation_summary(tool_name, updated),
            )
            state = self.adapter.get_state()

        clear_action = self._select_clear_action(request.message)
        if clear_action:
            operation, tool_name, target_id = clear_action
            remaining_steps = self._maybe_execute(
                request=request,
                remaining_steps=remaining_steps,
                actions=actions,
                tool_name=tool_name,
                target_id=target_id,
                action=operation,
                success_summary=lambda result: f"{tool_name} completed with status {result['status']}.",
            )
            state = self.adapter.get_state()

        snapshot = self.adapter.get_dashboard()
        fallback_answer = self._build_fallback_answer(request.message, state, actions, snapshot)
        llm_action_summaries = [item.summary for item in actions]
        answer = gemini_client.generate_agent_reply(
            message=request.message,
            state=state,
            fallback_text=fallback_answer,
            action_summaries=llm_action_summaries,
            model=settings.agent_model,
        )
        history = self.adapter.get_chat_history() if state.account else []
        return AgentResponse(answer=answer, actions=actions, history=history, snapshot=snapshot)

    def _maybe_execute(
        self,
        *,
        request: AgentRequest,
        remaining_steps: int,
        actions: list[AgentActionResult],
        tool_name: str,
        target_id: str | None,
        action: Callable[[], object],
        success_summary: Callable[[object], str],
    ) -> int:
        if remaining_steps <= 0:
            actions.append(
                AgentActionResult(
                    tool_name=tool_name,
                    status="skipped",
                    summary=f"{tool_name} was skipped because the agent reached its step limit.",
                    target_id=target_id,
                )
            )
            return remaining_steps

        if not request.allow_mutations:
            actions.append(
                AgentActionResult(
                    tool_name=tool_name,
                    status="skipped",
                    summary=f"{tool_name} was requested but skipped because safe mutations are disabled for this run.",
                    target_id=target_id,
                )
            )
            return remaining_steps

        try:
            result = action()
        except Exception as exc:
            actions.append(
                AgentActionResult(
                    tool_name=tool_name,
                    status="failed",
                    summary=f"{tool_name} failed: {exc}",
                    target_id=target_id,
                )
            )
            return remaining_steps - 1

        actions.append(
            AgentActionResult(
                tool_name=tool_name,
                status="executed",
                summary=success_summary(result),
                target_id=target_id,
            )
        )
        return remaining_steps - 1

    def _build_demo_account_input(self) -> AccountInput:
        return AccountInput(
            student_name="Prism Demo User",
            email="demo@cloud-optimizer.local",
            aws_account_id="123456789012",
            connection_mode="mocked",
            access_key_id="AKIA-DEMO-ACCOUNT",
            secret_access_key="demo-secret-placeholder",
            session_token="",
            region="ap-south-1",
            institution="Cloud Optimizer Demo",
        )

    def _build_recommendation_summary(self, tool_name: str, recommendation: Recommendation) -> str:
        verb = {
            "accept_recommendation": "Accepted",
            "reject_recommendation": "Rejected",
            "recur_recommendation": "Replayed",
        }[tool_name]
        return f"{verb} {recommendation.title} ({recommendation.id}), which now has status {recommendation.status}."

    def _build_fallback_answer(self, message: str, state: AppState, actions: list[AgentActionResult], snapshot) -> str:
        if actions:
            executed = [item for item in actions if item.status == "executed"]
            if executed:
                open_count = len([item for item in snapshot.recommendations if item.status == "open"])
                return (
                    f"{executed[-1].summary} The dashboard now shows ${snapshot.kpis.monthly_cost:.2f} in monthly cost, "
                    f"${snapshot.kpis.projected_savings:.2f} in remaining projected savings, and {open_count} open recommendations."
                )
            failed = [item for item in actions if item.status == "failed"]
            if failed:
                return failed[-1].summary
            return actions[-1].summary

        lowered = message.lower()
        if not state.account:
            return "No AWS account is linked yet. Connect a mocked or real account first so I can inspect recommendations and act on them safely."

        if "summary" in lowered or "posture" in lowered or "state" in lowered:
            open_count = len([item for item in snapshot.recommendations if item.status == "open"])
            accepted_count = len([item for item in snapshot.recommendations if item.status == "accepted"])
            return (
                f"The current posture shows ${snapshot.kpis.monthly_cost:.2f} in monthly cost, ${snapshot.kpis.projected_savings:.2f} "
                f"in remaining projected savings, {open_count} open recommendations, and {accepted_count} accepted changes."
            )

        next_action = self.adapter.suggest_next_action()
        return next_action["summary"]

    def _should_onboard_demo(self, message: str, state: AppState) -> bool:
        lowered = message.lower()
        if state.account is not None:
            return False
        return (
            ("link" in lowered or "connect" in lowered or "onboard" in lowered or "set up" in lowered)
            and ("demo" in lowered or "mock" in lowered or "mocked" in lowered or "account" in lowered)
        )

    def _select_recommendation_action(self, message: str) -> str | None:
        lowered = message.lower()
        if any(token in lowered for token in ("accept", "approve", "apply", "do it", "take it")):
            return "accept"
        if any(token in lowered for token in ("reject", "decline", "skip it")):
            return "reject"
        if any(token in lowered for token in ("replay", "recur", "repeat")):
            return "recur"
        return None

    def _select_clear_action(self, message: str) -> tuple[Callable[[], dict[str, str]], str, str] | None:
        lowered = message.lower()
        if "clear" not in lowered:
            return None
        if "chat" in lowered:
            return self.adapter.clear_chat_history, "clear_chat_history", "chat"
        if any(token in lowered for token in ("timeline", "events", "event feed")):
            return self.adapter.clear_events, "clear_events", "events"
        if any(token in lowered for token in ("observability", "metrics", "telemetry")):
            return self.adapter.clear_observability, "clear_observability", "observability"
        return None
