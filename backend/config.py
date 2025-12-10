from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    USE_CLOUD: bool = Field(False, description="Use cloud LLM provider", env="USE_CLOUD")
    OLLAMA_HOST: str = Field(
        "http://localhost:11434",
        description="Host URL for local Ollama server",
        env="OLLAMA_HOST",
    )
    OPENAI_API_KEY: Optional[str] = Field(
        None, description="API key for cloud LLM provider", env="OPENAI_API_KEY"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
