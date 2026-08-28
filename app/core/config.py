from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "NOVA"
    APP_ENV: str = "production"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/nova"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5434/nova"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & JWT Tokens
    JWT_SECRET: str = "supersecretjwtkey_change_me_in_production_min_32_characters"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AI Configuration (gemini | openai | ollama)
    AI_PROVIDER: str = "gemini"

    # Gemini (Google AI Studio Free Tier)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # OpenAI (gpt-4o-mini)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Ollama (Local-First)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3:8b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768

    # CORS
    CORS_ORIGINS: str = "*"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_async_db_url(cls, v: str) -> str:
        """Ensure PostgreSQL URL uses asyncpg driver in cloud environments (Heroku, Render, Supabase, Neon)."""
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def validate_sync_db_url(cls, v: str) -> str:
        """Ensure sync PostgreSQL URL uses psycopg2."""
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+psycopg2://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, str):
            if self.CORS_ORIGINS.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["*"]

    model_config = SettingsConfigDict(
        # Read directly from system environment variables (Docker/K8s/Cloud)
        # and fallback to .env or backend/.env if present
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
