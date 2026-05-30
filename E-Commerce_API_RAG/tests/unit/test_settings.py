import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.core.config import Settings

_PLACEHOLDER_SECRET = "your_secret_key_here_change_in_production"
_STRONG_SECRET = "a" * 48


def _minimal_settings(**overrides) -> dict:
    base = {
        "APP_NAME": "Test API",
        "APP_VERSION": "0.0.0",
        "DEBUG": True,
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5432,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "SECRET_KEY": "test-secret-key-for-unit-tests",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
        "REFRESH_TOKEN_EXPIRE_DAYS": 7,
    }
    base.update(overrides)
    return base


def test_secret_key_placeholder_allowed_in_debug():
    settings = Settings(**_minimal_settings(DEBUG=True, SECRET_KEY=_PLACEHOLDER_SECRET))
    assert settings.SECRET_KEY == _PLACEHOLDER_SECRET


def test_secret_key_placeholder_rejected_in_production():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            **_minimal_settings(DEBUG=False, SECRET_KEY=_PLACEHOLDER_SECRET)
        )
    assert "SECRET_KEY must be changed in production" in str(exc_info.value)


def test_secret_key_empty_rejected_in_production():
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_minimal_settings(DEBUG=False, SECRET_KEY=""))
    assert "SECRET_KEY must be changed in production" in str(exc_info.value)


def test_secret_key_strong_allowed_in_production():
    settings = Settings(**_minimal_settings(DEBUG=False, SECRET_KEY=_STRONG_SECRET))
    assert settings.SECRET_KEY == _STRONG_SECRET


def test_rag_commit_batch_size_default():
    settings = Settings(**_minimal_settings())
    assert settings.RAG_COMMIT_BATCH_SIZE == 10
