"""Configuration for Fastrr: LLM provider and model, loaded from environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FastrrConfig(BaseSettings):
    """
    Reads from environment variables (or a .env file).

    Variables:
        FASTRR_PROVIDER    - "ollama" (default) or "openrouter"
        FASTRR_MODEL       - model id, e.g. "llama3.2" or "openai/gpt-4o"
        OPENROUTER_API_KEY - required when provider is "openrouter"
        OLLAMA_HOST        - Ollama server URL (default: http://localhost:11434)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    provider: Literal["ollama", "openrouter"] = Field(
        default="ollama", validation_alias="FASTRR_PROVIDER"
    )
    model: str = Field(default="llama3.2", validation_alias="FASTRR_MODEL")
    openrouter_api_key: str | None = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    ollama_host: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_HOST"
    )
