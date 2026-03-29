from __future__ import annotations

from typing import Any

import requests

from .config import settings
from .models import AppState, Recommendation


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key or settings.google_api_key
        self.model = settings.gemini_model
        self.base_url = settings.gemini_api_base.rstrip("/")
        self.timeout_seconds = settings.gemini_timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_chat_reply(self, message: str, state: AppState, fallback_text: str) -> str:
        if not self.enabled:
            return fallback_text

        prompt = self._build_prompt(message, state, fallback_text)
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 350,
            },
        }

        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return fallback_text

        return self._extract_text(data) or fallback_text

    def _build_prompt(self, message: str, state: AppState, fallback_text: str) -> str:
        connection_mode = state.account.connection_mode if state.account else "none"
        resources = "\n".join(
            f"- {item.service} {item.name}: cost=${item.monthly_cost:.2f}, utilization={item.utilization}%, health={item.health_score}, alerts={item.alerts}, status={item.status}"
            for item in state.resources
        ) or "- No linked resources yet"
        recommendations = "\n".join(
            f"- {item.title} [{item.status}] saves=${item.projected_savings:.2f}: {item.rationale}"
            for item in state.recommendations
        ) or "- No recommendations yet"
        recent_events = "\n".join(
            f"- {item.title}: {item.description}"
            for item in state.events[:5]
        ) or "- No recent events"

        return (
            "You are Prism, a cloud optimization copilot for a student AWS demo app.\n"
            "Keep replies concise, specific, and grounded in the provided state only.\n"
            "Do not invent live AWS inventory or costs. Even in real AWS mode, this app may seed demo resources for visualization.\n"
            "If asked about actions, focus on simulated recommendation impact.\n\n"
            f"User message:\n{message}\n\n"
            "Current app state:\n"
            f"Connection mode: {connection_mode}\n"
            f"Resources:\n{resources}\n\n"
            f"Recommendations:\n{recommendations}\n\n"
            f"Recent events:\n{recent_events}\n\n"
            f"If the question is ambiguous, use this grounded fallback direction:\n{fallback_text}"
        )

    def _extract_text(self, payload: dict[str, Any]) -> str | None:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            parts = candidate.get("content", {}).get("parts", [])
            texts = [part.get("text", "") for part in parts if part.get("text")]
            if texts:
                return "\n".join(texts).strip()
        return None


def top_open_recommendation(state: AppState) -> Recommendation | None:
    return next((item for item in state.recommendations if item.status == "open"), None)


gemini_client = GeminiClient()
