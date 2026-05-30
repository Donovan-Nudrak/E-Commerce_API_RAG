import os
import sys
from collections.abc import Generator
from decimal import Decimal
from pathlib import Path

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_POSTGRES_PORT = os.environ.get("TEST_POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_PORT", TEST_POSTGRES_PORT)

# Set test environment before importing app modules
os.environ.setdefault("APP_NAME", "Ecommerce Test")
os.environ.setdefault("APP_VERSION", "0.0.1")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("UPLOAD_DIR", "uploads")
os.environ.setdefault("MEDIA_URL_PREFIX", "/media")

from app.core.security import hash_password  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.payment_type import PaymentType  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.role import Role  # noqa: E402
from main import app  # noqa: E402

TEST_DATABASE_URL = (
    f"postgresql+psycopg2://test:test@localhost:{TEST_POSTGRES_PORT}/test"
)


@pytest.fixture(scope="session")
def test_postgres_engine():
    try:
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL test database unavailable: {exc}")

    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def fake_redis_server():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def db_session(
    test_postgres_engine, fake_redis_server
) -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=test_postgres_engine)
    Base.metadata.create_all(bind=test_postgres_engine)
    session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_postgres_engine
    )
    session = session_local()
    try:
        customer_role = Role(name="Customer")
        admin_role = Role(name="Administrator")
        session.add_all([customer_role, admin_role])
        session.flush()

        session.add(
            Customer(
                role_id=admin_role.id,
                first_name="Admin",
                last_name="Ecommerce",
                email="admin@ecommerce.com",
                password_hash=hash_password("admin1234"),
            )
        )
        session.add(
            Category(name="Electronics")
        )
        session.flush()

        category = session.query(Category).first()
        session.add(
            Product(
                category_id=category.id,
                name="Test Product",
                description="Test",
                price=Decimal("100.00"),
                discount_price=Decimal("80.00"),
                stock=50,
                is_active=True,
            )
        )
        session.add_all(
            [
                PaymentType(name="Card"),
                PaymentType(name="Bank Transfer"),
                PaymentType(name="Cash"),
            ]
        )
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_postgres_engine)
        if hasattr(app.state, "limiter"):
            app.state.limiter.reset()


@pytest.fixture
def client(db_session: Session, fake_redis_server) -> Generator[TestClient, None, None]:
    async def override_get_redis():
        return fake_redis_server

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def customer_auth(client: TestClient) -> dict:
    email = "customer_test@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "Customer",
            "email": email,
            "password": "password123",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth(client: TestClient) -> dict:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ecommerce.com", "password": "admin1234"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def product_id(db_session: Session) -> int:
    return db_session.query(Product).first().id


@pytest.fixture
def payment_type_ids(db_session: Session) -> dict:
    card = db_session.query(PaymentType).filter(PaymentType.name == "Card").first()
    return {"card": card.id}
