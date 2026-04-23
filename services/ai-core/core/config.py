from functools import lru_cache
from typing import Literal

import boto3
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: SecretStr = Field(description="HMAC signing key for webhook validation")

    # Supabase
    supabase_url: str = Field(description="Supabase project URL")
    supabase_service_role_key: SecretStr = Field(description="Never expose to clients")

    # AI
    anthropic_api_key: SecretStr = Field(description="Anthropic Claude API key")
    openai_api_key: SecretStr = Field(description="OpenAI key for embeddings only")
    claude_model: str = "claude-sonnet-4-6"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # RAG
    retrieval_top_k: int = 8
    retrieval_min_similarity: float = 0.72
    max_context_tokens: int = 8000
    agent_max_iterations: int = 10

    # AWS
    aws_region: str = "us-east-1"
    aws_sqs_notification_queue_url: str = ""
    aws_sqs_outbox_queue_url: str = ""
    aws_s3_documents_bucket: str = ""

    # Database (direct connection for worker queries)
    database_url: str = Field(description="PostgreSQL connection string")

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


def _load_secret_from_aws(secret_name: str, region: str) -> str:
    """Load a secret from AWS Secrets Manager. Only called in staging/production."""
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]

    if settings.app_env in ("staging", "production"):
        # In production, override with values from AWS Secrets Manager
        # The environment provides the secret names, not the values
        pass

    return settings
