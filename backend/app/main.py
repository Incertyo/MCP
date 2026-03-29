from __future__ import annotations

from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .aws_client import AwsValidationError
from .config import settings
from .datadog import telemetry
from .models import AccountInput, ChatRequest
from .repository import build_repository
from .services import PrismService

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
service = PrismService(build_repository())


@app.middleware("http")
async def instrument_requests(request: Request, call_next):
    start = perf_counter()
    try:
        response = await call_next(request)
        return response
    except Exception:
        telemetry.increment("api.errors")
        raise
    finally:
        telemetry.gauge("api.latency_ms", round((perf_counter() - start) * 1000, 2))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/account")
def get_account():
    return service.get_account()


@app.post(f"{settings.api_prefix}/account")
def create_account(payload: AccountInput):
    try:
        return service.onboard_account(payload)
    except AwsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/dashboard")
def get_dashboard():
    telemetry.increment("dashboard.requests")
    return service.get_dashboard()


@app.get(f"{settings.api_prefix}/recommendations")
def get_recommendations():
    return service.list_recommendations()


@app.post(f"{settings.api_prefix}/recommendations/{{recommendation_id}}/accept")
def accept_recommendation(recommendation_id: str):
    try:
        return service.update_recommendation(recommendation_id, "accepted")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Recommendation not found") from exc


@app.post(f"{settings.api_prefix}/recommendations/{{recommendation_id}}/reject")
def reject_recommendation(recommendation_id: str):
    try:
        return service.update_recommendation(recommendation_id, "rejected")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Recommendation not found") from exc


@app.post(f"{settings.api_prefix}/recommendations/{{recommendation_id}}/recur")
def recur_recommendation(recommendation_id: str):
    try:
        return service.recur_recommendation(recommendation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Recommendation not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/events")
def get_events():
    return service.get_events()


@app.post(f"{settings.api_prefix}/events/clear")
def clear_events():
    return service.clear_events()


@app.get(f"{settings.api_prefix}/chat")
def get_chat_history():
    return service.get_chat_history()


@app.post(f"{settings.api_prefix}/chat")
def post_chat_message(payload: ChatRequest):
    return service.chat(payload.message)


@app.post(f"{settings.api_prefix}/chat/clear")
def clear_chat_history():
    return service.clear_chat_history()


@app.get(f"{settings.api_prefix}/observability")
def get_observability():
    return telemetry.summary()


@app.post(f"{settings.api_prefix}/observability/clear")
def clear_observability():
    return service.clear_observability()
