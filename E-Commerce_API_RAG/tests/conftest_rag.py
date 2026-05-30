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

os.environ.setdefault("APP_NAME", "Ecommerce RAG Test")
os.environ.setdefault("APP_VERSION", "0.0.1")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-rag-pytest-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("UPLOAD_DIR", "uploads")
os.environ.setdefault("MEDIA_URL_PREFIX", "/media")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

from app.core.security import hash_password  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database import session as db_session_module  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.models import (  # noqa: E402, F401
    Address,
    Cart,
    CartItem,
    Category,
    Customer,
    Order,
    OrderItem,
    PaymentType,
    Product,
    Role,
    UserPaymentMethod,
)
from app.models.category import Category as CategoryModel  # noqa: E402
from app.models.customer import Customer as CustomerModel  # noqa: E402
from app.models.product import Product as ProductModel  # noqa: E402
from app.models.role import Role as RoleModel  # noqa: E402
from main import app  # noqa: E402

RAG_POSTGRES_PORT = os.environ.get("TEST_POSTGRES_PORT", "5432")
RAG_DATABASE_URL = (
    f"postgresql+psycopg2://test_rag:test_rag@localhost:{RAG_POSTGRES_PORT}/test_rag"
)

pytest_plugins: list[str] = []


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_postgres: RAG tests requiring PostgreSQL pgvector and Gemini API",
    )


def _seed_rag_data(session: Session) -> dict[str, int]:
    customer_role = RoleModel(name="Customer")
    admin_role = RoleModel(name="Administrator")
    session.add_all([customer_role, admin_role])
    session.flush()

    session.add(
        CustomerModel(
            role_id=admin_role.id,
            first_name="Admin",
            last_name="RAG",
            email="admin@ecommerce.com",
            password_hash=hash_password("admin1234"),
        )
    )
    session.add(
        CustomerModel(
            role_id=customer_role.id,
            first_name="Customer",
            last_name="RAG",
            email="customer_rag@test.com",
            password_hash=hash_password("password123"),
        )
    )
    category = CategoryModel(name="Electronics")
    session.add(category)
    session.flush()

    bluetooth = ProductModel(
        category_id=category.id,
        name="Auriculares Bluetooth Test",
        description="Auriculares inalambricos con cancelacion de ruido",
        price=Decimal("49.99"),
        discount_price=Decimal("29.99"),
        stock=10,
        is_active=True,
    )
    laptop = ProductModel(
        category_id=category.id,
        name="Laptop RAG Test",
        description="Laptop para pruebas RAG",
        price=Decimal("999.99"),
        discount_price=None,
        stock=5,
        is_active=True,
    )
    mouse = ProductModel(
        category_id=category.id,
        name="Mouse RAG Test",
        description="Mouse ergonomico",
        price=Decimal("25.00"),
        discount_price=Decimal("19.99"),
        stock=20,
        is_active=True,
    )
    inactive = ProductModel(
        category_id=category.id,
        name="Producto Inactivo RAG",
        description="No debe indexarse ni aparecer en busqueda",
        price=Decimal("10.00"),
        stock=10,
        is_active=False,
    )
    no_stock = ProductModel(
        category_id=category.id,
        name="Producto Sin Stock RAG",
        description="Activo pero sin stock",
        price=Decimal("15.00"),
        stock=0,
        is_active=True,
    )
    session.add_all([bluetooth, laptop, mouse, inactive, no_stock])
    session.commit()

    return {
        "bluetooth_id": bluetooth.id,
        "inactive_id": inactive.id,
        "no_stock_id": no_stock.id,
    }


@pytest.fixture(scope="session")
def rag_postgres_engine():
    try:
        engine = create_engine(RAG_DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL RAG database unavailable: {exc}")

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def rag_db_session(rag_postgres_engine) -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=rag_postgres_engine)
    Base.metadata.create_all(bind=rag_postgres_engine)
    with rag_postgres_engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()

    session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=rag_postgres_engine
    )
    session = session_local()
    try:
        _seed_rag_data(session)
        yield session
    finally:
        session.close()


@pytest.fixture
def rag_product_ids(rag_db_session: Session) -> dict[str, int]:
    bluetooth = (
        rag_db_session.query(ProductModel)
        .filter(ProductModel.name == "Auriculares Bluetooth Test")
        .one()
    )
    inactive = (
        rag_db_session.query(ProductModel)
        .filter(ProductModel.name == "Producto Inactivo RAG")
        .one()
    )
    no_stock = (
        rag_db_session.query(ProductModel)
        .filter(ProductModel.name == "Producto Sin Stock RAG")
        .one()
    )
    return {
        "bluetooth_id": bluetooth.id,
        "inactive_id": inactive.id,
        "no_stock_id": no_stock.id,
    }


@pytest.fixture(scope="session")
def fake_redis_server_rag():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def rag_client(
    rag_db_session: Session,
    rag_postgres_engine,
    fake_redis_server_rag,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    rag_session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=rag_postgres_engine
    )
    monkeypatch.setattr(db_session_module, "engine", rag_postgres_engine)
    monkeypatch.setattr(db_session_module, "SessionLocal", rag_session_factory)

    async def override_get_redis():
        return fake_redis_server_rag

    def override_get_db():
        try:
            yield rag_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()


@pytest.fixture
def require_gemini_key():
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return

    if os.environ.get("CI", "").lower() == "true":
        pytest.fail(
            "GEMINI_API_KEY secret is not configured in GitHub Actions"
        )

    pytest.skip("GEMINI_API_KEY not set — skipping RAG tests locally")


@pytest.fixture
def rag_admin_auth(rag_client: TestClient) -> dict[str, str]:
    login = rag_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ecommerce.com", "password": "admin1234"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def rag_admin_token(rag_admin_auth: dict[str, str]) -> str:
    return rag_admin_auth["Authorization"].removeprefix("Bearer ")


@pytest.fixture
def rag_customer_auth(rag_client: TestClient) -> dict[str, str]:
    login = rag_client.post(
        "/api/v1/auth/login",
        json={"email": "customer_rag@test.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
