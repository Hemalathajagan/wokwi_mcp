"""Application configuration loaded from environment / .env file."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = "CHANGE-ME-to-a-random-secret-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./wokwi_analyzer.db"

    model_config = {"env_file": str(ENV_PATH), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
