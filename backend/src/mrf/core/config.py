"""Application configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://192.168.79.42"])
    log_level: str = "INFO"
    api_port: int = 8000


settings = Settings()
