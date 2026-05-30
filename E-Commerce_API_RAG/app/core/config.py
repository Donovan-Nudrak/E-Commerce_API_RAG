from pydantic import model_validator
from pydantic_settings import BaseSettings

_INSECURE_SECRET_PLACEHOLDERS = frozenset({
    "",
    "your_secret_key_here_change_in_production",
})


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    UPLOAD_DIR: str = "uploads"
    MEDIA_URL_PREFIX: str = "/media"

    # Optional: comma-separated browser origins (e.g. https://app.example.com).
    # Leave empty to disable CORS (recommended for API-only / Postman / server clients).
    CORS_ALLOWED_ORIGINS: str = ""

    # Optional: base URL for password-reset links in emails (e.g. https://app.example.com).
    # If empty, the email includes the token for manual use via POST /auth/reset-password.
    PASSWORD_RESET_BASE_URL: str = ""

    GEMINI_API_KEY: str = ""
    RAG_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    RAG_GENERATION_MODEL: str = "gemini-2.5-flash"
    RAG_EMBEDDING_DIM: int = 768
    RAG_COMMIT_BATCH_SIZE: int = 10
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    RAG_CANDIDATE_MULTIPLIER: int = 3
    RAG_GEMINI_TIMEOUT: int = 30
    RAG_MAX_HISTORY: int = 10

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def _validate_secret_key_for_production(self) -> "Settings":
        if self.DEBUG:
            return self
        key = (self.SECRET_KEY or "").strip()
        if key in _INSECURE_SECRET_PLACEHOLDERS:
            raise ValueError(
                "SECRET_KEY must be changed in production. Set a strong random key in .env"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        if not self.CORS_ALLOWED_ORIGINS.strip():
            return []
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
