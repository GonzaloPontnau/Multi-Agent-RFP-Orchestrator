from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada del backend con validación de tipos."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Groq
    groq_api_key: str = Field(..., min_length=1)
    groq_model: str = Field(default="openai/gpt-oss-120b")

    # HuggingFace (for API-based embeddings - saves RAM on free tier)
    huggingface_api_key: str = Field(..., min_length=1)

    # RAG Settings (Qdrant in-memory - no external credentials needed)
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    ingestion_batch_size: int = Field(default=50, ge=1, le=500)

    # Pipeline settings
    retrieval_k: int = Field(default=10, ge=1, le=50)
    grader_doc_truncation: int = Field(default=1500, ge=200, le=10000)
    safety_net_min_docs: int = Field(default=3, ge=1, le=20)
    safety_net_fallback_docs: int = Field(default=5, ge=1, le=20)
    max_audit_revisions: int = Field(default=2, ge=0, le=10)
    context_max_chars: int = Field(default=6000, ge=500, le=30000)
    answer_max_chars: int = Field(default=3000, ge=100, le=20000)

    # Model temperatures
    router_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    grader_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    refine_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    quant_extract_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    quant_insight_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    risk_temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    # API cache
    cache_ttl_seconds: int = Field(default=300, ge=10, le=86400)
    cache_max_size: int = Field(default=100, ge=1, le=10000)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado para evitar recargar .env en cada request."""
    return Settings()


settings = get_settings()
