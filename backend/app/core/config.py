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
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # HuggingFace (for API-based embeddings - saves RAM on free tier)
    huggingface_api_key: str = Field(..., min_length=1)

    # RAG Settings (Qdrant in-memory - no external credentials needed)
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado para evitar recargar .env en cada request."""
    return Settings()


settings = get_settings()
