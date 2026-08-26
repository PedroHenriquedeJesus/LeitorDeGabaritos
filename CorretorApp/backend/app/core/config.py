from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CorretorApp"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{Path(__file__).resolve().parents[3] / 'backend' / 'corretorapp.db'}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    initial_admin_username: str = ""
    initial_admin_password: str = ""
    auth_session_hours: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
