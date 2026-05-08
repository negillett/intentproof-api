from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = Field(default="dev", alias="INTENTPROOF_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/intentproof_api",
        alias="INTENTPROOF_DATABASE_URL",
    )
    api_keys: dict[str, str] = Field(default_factory=dict, alias="INTENTPROOF_API_KEYS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
