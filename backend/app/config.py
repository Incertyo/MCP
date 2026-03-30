import os
import tempfile
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_file() -> Path:
    if os.getenv("VERCEL"):
        return Path(tempfile.gettempdir()) / "cloud_optimizer_mcp_state.json"
    return Path(__file__).resolve().parents[1] / ".local" / "prism_state.json"


class Settings(BaseSettings):
    app_name: str = "Prism Cloud Optimizer Demo"
    api_prefix: str = "/api"
    data_file: Path = Field(default_factory=default_data_file, alias="PRISM_DATA_FILE")
    use_dynamodb: bool = Field(default=False, alias="PRISM_USE_DYNAMODB")
    dynamodb_region: str = Field(default="ap-south-1", alias="PRISM_DYNAMODB_REGION")
    dynamodb_table_prefix: str = Field(default="prism_demo", alias="PRISM_DYNAMODB_TABLE_PREFIX")
    dd_api_key: str | None = Field(default=None, alias="DD_API_KEY")
    dd_app_key: str | None = Field(default=None, alias="DD_APP_KEY")
    dd_site: str = Field(default="datadoghq.com", alias="DD_SITE")
    dd_env: str = Field(default="demo", alias="DD_ENV")
    dd_service: str = Field(default="prism-backend", alias="DD_SERVICE")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_api_base: str = Field(default="https://generativelanguage.googleapis.com/v1beta", alias="GEMINI_API_BASE")
    gemini_timeout_seconds: float = Field(default=20.0, alias="GEMINI_TIMEOUT_SECONDS")
    frontend_origin: str = Field(default="http://localhost:5173", alias="PRISM_FRONTEND_ORIGIN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


settings = Settings()
