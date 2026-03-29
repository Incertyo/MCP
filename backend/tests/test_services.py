from pathlib import Path

from app.models import AccountInput
from app.repository import LocalJsonRepository
from app.services import PrismService


def build_service(tmp_path: Path) -> PrismService:
    return PrismService(LocalJsonRepository(tmp_path / "state.json"))


def test_onboard_account_seeds_demo_state(tmp_path: Path):
    service = build_service(tmp_path)
    account = service.onboard_account(
        AccountInput(
            student_name="Mohan",
            email="mohan@example.com",
            aws_account_id="1234567890",
            connection_mode="mocked",
            access_key_id="AKIA****",
            secret_access_key="****demo",
        )
    )
    dashboard = service.get_dashboard()
    assert account.connected is True
    assert len(dashboard.resources) == 4
    assert len(dashboard.recommendations) == 3


def test_accepting_recommendation_updates_dashboard(tmp_path: Path):
    service = build_service(tmp_path)
    service.onboard_account(
        AccountInput(
            student_name="Mohan",
            email="mohan@example.com",
            aws_account_id="1234567890",
            connection_mode="mocked",
            access_key_id="AKIA****",
            secret_access_key="****demo",
        )
    )
    recommendation = service.update_recommendation("rec-ec2-rightsize", "accepted")
    dashboard = service.get_dashboard()
    target = next(item for item in dashboard.resources if item.id == recommendation.target_resource_id)
    assert recommendation.status == "accepted"
    assert target.status == "Optimized"
    assert dashboard.kpis.monthly_cost < 166.5


def test_chat_mentions_next_best_action(tmp_path: Path):
    service = build_service(tmp_path)
    service.onboard_account(
        AccountInput(
            student_name="Mohan",
            email="mohan@example.com",
            aws_account_id="1234567890",
            connection_mode="mocked",
            access_key_id="AKIA****",
            secret_access_key="****demo",
        )
    )
    response = service.chat("What should I do next?")
    assert "next best action" in response.reply.content.lower()
