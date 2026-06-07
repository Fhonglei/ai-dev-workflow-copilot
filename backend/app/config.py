from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Dev Workflow Copilot"
    app_version: str = "1.0.0"
    environment: str = "development"

    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str = r"https://.*\.vercel\.app"
    database_path: str = "data/workflow.db"

    github_token: str = ""
    github_webhook_secret: str = ""

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = Field(default=30, ge=5, le=120)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def llm_configured(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def github_configured(self) -> bool:
        return bool(self.github_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
