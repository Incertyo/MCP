from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

from .config import settings
from .models import EventItem, ObservabilitySummary, TelemetryMetric


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DatadogTelemetry:
    def __init__(self) -> None:
        self._metrics: dict[str, float] = defaultdict(float)
        self._timestamps: dict[str, datetime] = {}
        self._recent_events: list[EventItem] = []

    def increment(self, name: str, value: float = 1.0) -> None:
        self._metrics[name] += value
        self._timestamps[name] = utcnow()
        self._send_metric(name, self._metrics[name])

    def gauge(self, name: str, value: float) -> None:
        self._metrics[name] = value
        self._timestamps[name] = utcnow()
        self._send_metric(name, value)

    def event(self, title: str, text: str, tags: list[str] | None = None) -> EventItem:
        event = EventItem(
            id=f"dd-{len(self._recent_events) + 1}",
            type="observability",
            title=title,
            description=text,
            created_at=utcnow(),
        )
        self._recent_events = [event, *self._recent_events][:8]
        self._send_event(title, text, tags or [])
        return event

    def summary(self) -> ObservabilitySummary:
        metrics = [
            TelemetryMetric(name=name, value=value, last_updated=self._timestamps.get(name, utcnow()))
            for name, value in sorted(self._metrics.items())
        ]
        status = "healthy" if self._metrics.get("api.errors", 0) == 0 else "degraded"
        return ObservabilitySummary(status=status, metrics=metrics, recent_events=list(self._recent_events))

    def clear(self) -> None:
        self._metrics.clear()
        self._timestamps.clear()
        self._recent_events.clear()

    def _send_metric(self, name: str, value: float) -> None:
        if not settings.dd_api_key:
            return
        payload: dict[str, Any] = {
            "series": [
                {
                    "metric": f"prism.{name}",
                    "points": [[int(utcnow().timestamp()), value]],
                    "type": 3,
                    "tags": [f"env:{settings.dd_env}", f"service:{settings.dd_service}"],
                }
            ]
        }
        url = f"https://api.{settings.dd_site}/api/v2/series"
        try:
            headers = {"DD-API-KEY": settings.dd_api_key}
            if settings.dd_app_key:
                headers["DD-APPLICATION-KEY"] = settings.dd_app_key
            requests.post(url, json=payload, headers=headers, timeout=2)
        except requests.RequestException:
            return

    def _send_event(self, title: str, text: str, tags: list[str]) -> None:
        if not settings.dd_api_key:
            return
        payload = {
            "title": title,
            "text": text,
            "tags": tags + [f"env:{settings.dd_env}", f"service:{settings.dd_service}"],
        }
        url = f"https://api.{settings.dd_site}/api/v1/events"
        try:
            headers = {"DD-API-KEY": settings.dd_api_key}
            if settings.dd_app_key:
                headers["DD-APPLICATION-KEY"] = settings.dd_app_key
            requests.post(url, json=payload, headers=headers, timeout=2)
        except requests.RequestException:
            return


telemetry = DatadogTelemetry()
