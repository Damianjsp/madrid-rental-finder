"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://mrf:mrf@localhost:5432/madrid_rental_finder"
    )
    log_level: str = "INFO"
    api_port: int = 8000


settings = Settings()
