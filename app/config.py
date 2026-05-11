from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = Field(default="dev", alias="INTENTPROOF_ENV")
    database_url: str = Field(alias="INTENTPROOF_DATABASE_URL")
    api_keys: dict[str, str] = Field(default_factory=dict, alias="INTENTPROOF_API_KEYS")
    sqs_queue_url: str | None = Field(default=None, alias="INTENTPROOF_SQS_QUEUE_URL")
    aws_region: str | None = Field(default=None, alias="INTENTPROOF_AWS_REGION")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
