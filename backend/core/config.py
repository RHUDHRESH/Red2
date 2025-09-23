# core/config.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    DotEnvSettingsSource,
)

# Paths
BACKEND_DIR = Path(__file__).resolve().parents[1]        # .../backend
REPO_ROOT = BACKEND_DIR.parent                            # project root
BACKEND_DOTENV = BACKEND_DIR / ".env"
ROOT_DOTENV = REPO_ROOT / ".env"

class Settings(BaseSettings):
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(None, description="Google Maps API key")
    GOOGLE_MAPS_BROWSER_API_KEY: Optional[str] = Field(
        None,
        description="Google Maps API key for frontend (restricted by HTTP referrer)",
    )
    EXPOSE_SERVER_MAPS_KEY_TO_FRONTEND: bool = Field(
        False,
        description="If true and no browser key provided, expose server key to frontend (local dev only)",
    )
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    OLLAMA_HOST: str = "localhost"
    OLLAMA_PORT: int = 11434
    OLLAMA_FAST_MODEL: str = "gemma3:1b"
    OLLAMA_REASONING_MODEL: str = "gemma3:4b"
    # Default embeddings model. Override in .env as needed.
    # If you require a specific family (e.g., Gemma-based embeddings), set
    # OLLAMA_EMBEDDINGS_MODEL in your .env and run `ollama pull <model>`.
    OLLAMA_EMBEDDINGS_MODEL: str = "jina-embeddings-v2-base-en"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def OLLAMA_BASE_URL(self) -> str:
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

    @model_validator(mode="after")
    def _soft_validate(self):
        # Keep configuration permissive; individual services will degrade gracefully
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings=None,
        file_secrets_settings=None,
        **kwargs,
    ):
        """Customize settings load order and support both pydantic-settings arg names.

        Some versions pass `file_secret_settings` (singular) and others
        `file_secrets_settings` (plural). Accept both gracefully.
        """
        backend_env = DotEnvSettingsSource(settings_cls, env_file=BACKEND_DOTENV, env_file_encoding="utf-8")
        root_env = DotEnvSettingsSource(settings_cls, env_file=ROOT_DOTENV, env_file_encoding="utf-8")
        file_settings = file_secret_settings or file_secrets_settings

        # Precedence: init > OS env > backend .env > root .env > file secrets
        return (
            init_settings,
            env_settings,
            backend_env,
            root_env,
            file_settings,
        )

settings = Settings()
