from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _repo_root() -> Path:
    """Repository root (parent of backend/)."""
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_repo_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Plum Claims Adjudication API"
    app_version: str = "0.1.0"
    policy_terms_path: Path = _repo_root() / "policy_terms.json"
    test_cases_path: Path = _repo_root() / "test_cases.json"
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./.data/claims.db"
    cors_origins: Annotated[list[str], BeforeValidator(_parse_csv_list)] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
        ]
    )
    cors_origin_regex: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
