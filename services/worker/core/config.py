from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = Field(description="Async PostgreSQL connection string")
    redis_url: str = Field(default="redis://localhost:6379/0")

    supabase_url: str = ""
    supabase_service_role_key: SecretStr = Field(default="")

    anthropic_api_key: SecretStr = Field(default="")
    openai_api_key: SecretStr = Field(default="")
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    notion_integration_token: SecretStr = Field(default="")

    aws_region: str = "us-east-1"
    aws_sqs_outbox_queue_url: str = ""
    aws_sqs_notification_queue_url: str = ""

    slack_bot_token: SecretStr = Field(default="")
    slack_operations_channel: str = "#operations"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return WorkerSettings()  # type: ignore[call-arg]
