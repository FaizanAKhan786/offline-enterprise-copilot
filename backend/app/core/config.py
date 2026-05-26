"""
Application configuration via environment variables with validation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "Offline Enterprise AI Copilot"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── Authentication ───────────────────────────────────────────
    jwt_secret: str = Field(default="CHANGE-ME-IN-PRODUCTION")
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 1440  # 24 hours
    default_admin_email: str = "admin@copilot.local"
    default_admin_password: str = "changeme-in-production"

    # ── Database ─────────────────────────────────────────────────
    postgres_dsn: str = "postgresql+asyncpg://copilot:copilot@localhost:5432/copilot"
    redis_url: str = "redis://localhost:6379/0"

    # ── Vector Store ─────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "documents"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    # ── LLM ──────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "llama3:8b"
    available_models: list[str] = [
        "llama3:8b",
        "mistral:7b",
        "qwen2:7b",
    ]
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_timeout: int = 120

    # ── RAG ──────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    rerank_top_k: int = 3
    hybrid_alpha: float = 0.7  # weight for dense vs sparse (1.0 = all dense)

    # ── Document Storage ─────────────────────────────────────────
    upload_dir: Path = Path("data/uploads")
    max_upload_size_mb: int = 100

    # ── Voice ────────────────────────────────────────────────────
    whisper_model: str = "base"

    # ── Translation ──────────────────────────────────────────────
    translation_model_prefix: str = "Helsinki-NLP/opus-mt"

    # ── Cache ────────────────────────────────────────────────────
    semantic_cache_ttl: int = 3600
    semantic_cache_threshold: float = 0.92

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Celery ───────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @field_validator("upload_dir")
    @classmethod
    def ensure_upload_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
