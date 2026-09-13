from typing import List, Union
import secrets
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "AI Model Gateway"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"

    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY_MIN_32_CHARS"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Database
    # Defaults to SQLite for immediate local dev/testing if Postgres is not running
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_gateway.db"
    DATABASE_ECHO: bool = False

    # Redis (Optional: if empty or connection fails, falls back to in-memory)
    REDIS_URL: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Gateway Limits & Concurrency (Optimized for Apple M5 16 GB Unified Memory)
    DEFAULT_RATE_LIMIT_RPM: int = 60
    DEFAULT_MONTHLY_TOKEN_LIMIT: int = 10_000_000
    DEFAULT_MAX_CONCURRENT_REQUESTS: int = 4
    DEFAULT_QUEUE_TIMEOUT_SECONDS: float = 30.0
    DEFAULT_REQUEST_TIMEOUT_SECONDS: float = 300.0

    # Per-Backend Concurrency Limits
    OLLAMA_CONCURRENCY: int = 2
    LLAMACPP_CONCURRENCY: int = 1
    MLX_CONCURRENCY: int = 2

    # Resilience & Retries
    MAX_RETRIES: int = 2
    RETRY_BACKOFF_FACTOR: float = 0.5
    PROVIDER_TIMEOUT_SECONDS: float = 120.0

    # Model Idle & Context Settings
    MODEL_IDLE_TIMEOUT_SECONDS: int = 300
    DEFAULT_MODEL: str = "universal"
    DEFAULT_CONTEXT_SIZE: int = 8192

    # Privacy
    # When False, prompts and completions are NEVER saved in logs or database
    STORE_REQUEST_CONTENT: bool = False

    # Admin bootstrap credentials & default key
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "admin123456"
    FIRST_ADMIN_NAME: str = "System Admin"
    GATEWAY_API_KEY: str = ""

    # Inference engine default internal endpoints on Apple Silicon M5
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    MLX_BASE_URL: str = "http://127.0.0.1:8081"
    LLAMACPP_BASE_URL: str = "http://127.0.0.1:8082"


settings = Settings()

