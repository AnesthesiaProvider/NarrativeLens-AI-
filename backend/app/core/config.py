"""Application configuration loaded from environment variables and .env file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NarrativeLens AI Application Settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Application Settings
    PROJECT_NAME: str = "NarrativeLens AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "narrativelens-development-secret-key-change-in-production"
    API_V1_STR: str = "/api"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]

    # Database Configuration (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "narrativelens"
    DATABASE_URL: Optional[str] = None
    ASYNC_DATABASE_URL: Optional[str] = None

    # Redis Cache & Task Queue
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    # Machine Learning & AI Models
    DEVICE: str = "auto"
    MODEL_CACHE_DIR: str = "./model_cache"
    HATE_SPEECH_MODEL_ID: str = "FacebookAI/xlm-roberta-base"
    EMBEDDING_MODEL_ID: str = "BAAI/bge-m3"
    MULTIMODAL_MODEL_ID: str = "Qwen/Qwen3-VL-4B-Instruct"
    CLASSIFIER_CHECKPOINT_PATH: str = "ml/checkpoints/xlm-roberta-hate-speech"
    CLASSIFIER_NUM_LABELS: int = 3
    CLASSIFIER_LABELS: List[str] = ["normal", "offensive", "hate"]
    BATCH_SIZE: int = 32
    MAX_SEQUENCE_LENGTH: int = 512

    # Storage & Ingestion
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # External APIs & Social Media
    YOUTUBE_API_KEY: Optional[str] = None

    # Local LLM Context Arbiter (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    ENABLE_LLM_CONTEXT_ARBITER: bool = True

    # Security & SSRF Protection
    BLOCKED_IP_NETWORKS: List[str] = [
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "0.0.0.0/8",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    ]
    ALLOWED_SOURCE_TYPES: List[str] = [
        "text",
        "url",
        "rss",
        "file",
        "csv",
        "json",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("BLOCKED_IP_NETWORKS", mode="before")
    @classmethod
    def assemble_blocked_networks(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def assemble_computed_fields(self) -> Settings:
        # Assemble synchronous database URL if not set
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        # Assemble async database URL if not set
        if not self.ASYNC_DATABASE_URL:
            self.ASYNC_DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        # Assemble Redis URL if not set
        if not self.REDIS_URL:
            password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

        # Ensure directory paths exist or are resolved
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.MODEL_CACHE_DIR).mkdir(parents=True, exist_ok=True)

        return self


settings = Settings()
