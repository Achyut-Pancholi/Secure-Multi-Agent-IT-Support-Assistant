import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Settings (Using OpenAI OSS models hosted on Groq)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # API Settings
    internal_api_url: str = "http://localhost:8001"
    
    # App Settings
    log_level: str = "INFO"
    app_env: str = "development"
    
    # Optional Langfuse Settings
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: Optional[str] = "https://cloud.langfuse.com"
    langfuse_base_url: Optional[str] = None

    @property
    def effective_langfuse_host(self) -> str:
        return self.langfuse_base_url or self.langfuse_host or "https://cloud.langfuse.com"

    def is_langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

settings = Settings()
