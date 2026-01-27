from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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

    # Pinecone
    pinecone_api_key: str = Field(..., min_length=1)
    pinecone_env: str = Field(default="us-east-1")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("ollama_base_url debe ser una URL válida")
        return v.rstrip("/")

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado para evitar recargar .env en cada request."""
    return Settings()


settings = get_settings()
