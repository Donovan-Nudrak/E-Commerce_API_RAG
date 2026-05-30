pytest_plugins = ["tests.conftest_rag"]

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.rag_service import NO_MATCH_ANSWER

pytestmark = pytest.mark.requires_postgres


def _index_products(client, rag_admin_auth: dict[str, str]) -> dict:
    response = client.post("/api/v1/rag/index", headers=rag_admin_auth)
    assert response.status_code == 200
    return response.json()


def _assert_sources_sorted_desc(sources: list[dict]) -> None:
    scores = [source["similarity_score"] for source in sources]
    assert scores == sorted(scores, reverse=True)


def test_rag_index_products(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
    rag_db_session: Session,
):
    active_count = (
        rag_db_session.query(Product)
        .filter(Product.is_active == True)
        .count()
    )
    assert active_count >= 3

    data = _index_products(rag_client, rag_admin_auth)
    assert data["errors"] == 0
    assert data["indexed"] >= 3

    active_with_stock = (
        rag_db_session.query(Product)
        .filter(
            Product.is_active == True,
            Product.stock > 0,
        )
        .all()
    )
    assert len(active_with_stock) >= 3
    for product in active_with_stock:
        assert product.embedding is not None
        assert product.indexed_at is not None


def test_rag_index_categories_without_prior_index(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
):
    response = rag_client.post(
        "/api/v1/rag/index/categories",
        headers=rag_admin_auth,
    )
    assert response.status_code == 409
    assert "Run /rag/index before /rag/index/categories" in response.json()["detail"]


def test_soft_delete_clears_embedding(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
    rag_db_session: Session,
    rag_product_ids: dict[str, int],
):
    _index_products(rag_client, rag_admin_auth)

    product_id = rag_product_ids["bluetooth_id"]
    product = rag_db_session.query(Product).filter(Product.id == product_id).one()
    assert product.embedding is not None
    assert product.indexed_at is not None

    delete_response = rag_client.delete(
        f"/api/v1/admin/products/{product_id}",
        headers=rag_admin_auth,
    )
    assert delete_response.status_code == 204

    rag_db_session.expire_all()
    product = rag_db_session.query(Product).filter(Product.id == product_id).one()
    assert product.is_active is False
    assert product.embedding is None
    assert product.indexed_at is None


def test_rag_query_returns_relevant_results(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
):
    _index_products(rag_client, rag_admin_auth)

    response = rag_client.post(
        "/api/v1/rag/query",
        json={"query": "auriculares bluetooth baratos"},
    )
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["answer"], str)
    assert len(data["answer"].strip()) > 0
    assert isinstance(data["sources"], list)
    assert data["query"] == "auriculares bluetooth baratos"

    for source in data["sources"]:
        assert source["similarity_score"] > 0

    _assert_sources_sorted_desc(data["sources"])

    source_names = [source["name"].lower() for source in data["sources"]]
    assert any(
        "auricular" in name or "bluetooth" in name for name in source_names
    )


def test_rag_query_filters_inactive_and_no_stock(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
    rag_product_ids: dict[str, int],
):
    _index_products(rag_client, rag_admin_auth)

    response = rag_client.post(
        "/api/v1/rag/query",
        json={"query": "productos electronicos"},
    )
    assert response.status_code == 200
    source_ids = {source["id"] for source in response.json()["sources"]}

    assert rag_product_ids["inactive_id"] not in source_ids
    assert rag_product_ids["no_stock_id"] not in source_ids


def test_rag_query_below_threshold_returns_honest_answer(
    require_gemini_key,
    rag_client,
):
    response = rag_client.post(
        "/api/v1/rag/query",
        json={"query": "equipamiento de laboratorio cuantico xyz"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["sources"] == []
    assert (
        "No encontré productos" in data["answer"]
        or "reformular" in data["answer"]
        or NO_MATCH_ANSWER in data["answer"]
    )


def test_rag_index_categories(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
):
    index_response = rag_client.post("/api/v1/rag/index", headers=rag_admin_auth)
    assert index_response.status_code == 200

    categories_response = rag_client.post(
        "/api/v1/rag/index/categories",
        headers=rag_admin_auth,
    )
    assert categories_response.status_code == 200
    data = categories_response.json()

    assert data["categories_processed"] >= 1
    assert data["products_updated"] >= 1
    assert data["errors"] == 0


def test_rag_query_without_api_key(rag_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    response = rag_client.post(
        "/api/v1/rag/query",
        json={"query": "auriculares"},
    )
    assert response.status_code == 503


def test_rag_index_requires_admin(rag_client, rag_customer_auth):
    no_auth = rag_client.post("/api/v1/rag/index")
    assert no_auth.status_code in (401, 403)

    customer = rag_client.post("/api/v1/rag/index", headers=rag_customer_auth)
    assert customer.status_code == 403
    assert customer.json()["detail"] == "Admin access required."


def test_rag_multiturn_conversation(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
):
    _index_products(rag_client, rag_admin_auth)

    turn_one = rag_client.post(
        "/api/v1/rag/query",
        json={"query": "qué auriculares tienen?", "history": []},
    )
    assert turn_one.status_code == 200
    turn_one_data = turn_one.json()
    assert len(turn_one_data["history"]) == 2
    assert turn_one_data["history"][0]["role"] == "user"
    assert turn_one_data["history"][1]["role"] == "assistant"

    turn_two = rag_client.post(
        "/api/v1/rag/query",
        json={
            "query": "tienen algo más barato?",
            "history": turn_one_data["history"],
        },
    )
    assert turn_two.status_code == 200
    turn_two_data = turn_two.json()
    assert len(turn_two_data["history"]) == 4

    answer_lower = turn_two_data["answer"].lower()
    assert any(
        keyword in answer_lower
        for keyword in ("auricular", "bluetooth", "barato", "precio", "$")
    )


def test_rag_history_limit(
    require_gemini_key,
    rag_client,
    rag_admin_auth,
):
    _index_products(rag_client, rag_admin_auth)

    long_history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"Mensaje de prueba {index}",
        }
        for index in range(10)
    ]

    response = rag_client.post(
        "/api/v1/rag/query",
        json={
            "query": "auriculares disponibles",
            "history": long_history,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["answer"].strip()) > 0
    assert len(data["history"]) == 12
