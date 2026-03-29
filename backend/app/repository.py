from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .config import settings
from .models import AppState

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception


class StateRepository(ABC):
    @abstractmethod
    def load_state(self) -> AppState:
        raise NotImplementedError

    @abstractmethod
    def save_state(self, state: AppState) -> None:
        raise NotImplementedError


class LocalJsonRepository(StateRepository):
    def __init__(self, data_file: Path) -> None:
        self.data_file = data_file
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> AppState:
        if not self.data_file.exists():
            return AppState()
        try:
            payload = json.loads(self.data_file.read_text(encoding="utf-8"))
            state = AppState.model_validate(payload)
            # Best-effort scrubbing of legacy / sensitive fields that may exist in persisted state.
            if isinstance(payload, dict) and isinstance(payload.get("account"), dict):
                legacy_keys = {"access_key_id", "secret_access_key", "session_token", "access_key_hint", "secret_key_hint"}
                if legacy_keys.intersection(payload["account"].keys()):
                    try:
                        self.save_state(state)
                    except OSError:
                        pass
            return state
        except (OSError, json.JSONDecodeError, ValidationError):
            broken_name = f"{self.data_file.stem}.broken.{int(time.time())}{self.data_file.suffix}"
            try:
                self.data_file.rename(self.data_file.with_name(broken_name))
            except OSError:
                pass
            return AppState()

    def save_state(self, state: AppState) -> None:
        self.data_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")


class DynamoRepository(StateRepository):
    collections = ("accounts", "resources", "recommendations", "chat_messages", "events")

    def __init__(self) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB mode")
        self.resource = boto3.resource("dynamodb", region_name=settings.dynamodb_region)

    def _table(self, name: str):
        return self.resource.Table(f"{settings.dynamodb_table_prefix}_{name}")

    def load_state(self) -> AppState:
        try:
            payload: dict[str, Any] = {}
            for collection in self.collections:
                items = self._table(collection).scan().get("Items", [])
                payload[collection if collection != "accounts" else "account"] = items
            payload["account"] = payload["account"][0] if payload.get("account") else None
            return AppState.model_validate(payload)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Failed to load state from DynamoDB") from exc

    def save_state(self, state: AppState) -> None:
        try:
            self._replace_collection("accounts", [state.account.model_dump(mode="json")] if state.account else [])
            self._replace_collection("resources", [item.model_dump(mode="json") for item in state.resources])
            self._replace_collection("recommendations", [item.model_dump(mode="json") for item in state.recommendations])
            self._replace_collection("chat_messages", [item.model_dump(mode="json") for item in state.chat_messages])
            self._replace_collection("events", [item.model_dump(mode="json") for item in state.events])
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Failed to save state to DynamoDB") from exc

    def _replace_collection(self, collection: str, items: list[dict[str, Any]]) -> None:
        table = self._table(collection)
        existing = table.scan().get("Items", [])
        with table.batch_writer() as batch:
            for item in existing:
                batch.delete_item(Key={"id": item["id"]})
            for item in items:
                batch.put_item(Item=item)


def build_repository() -> StateRepository:
    if settings.use_dynamodb:
        try:
            return DynamoRepository()
        except RuntimeError:
            pass
    return LocalJsonRepository(settings.data_file)
