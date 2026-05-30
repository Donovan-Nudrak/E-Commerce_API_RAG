from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from app.schemas.rag import RAGMessage
from app.services.rag_service import (
    NO_MATCH_ANSWER,
    CategoryStats,
    RAGService,
)


def _make_category(name: str = "Electronics") -> MagicMock:
    category = MagicMock()
    category.name = name
    return category


def _make_product(
    product_id: int = 1,
    *,
    name: str = "Test Product",
    category_id: int = 1,
    price: str = "100.00",
    discount_price: str | None = None,
    stock: int = 50,
    description: str = "Test description",
) -> MagicMock:
    product = MagicMock()
    product.id = product_id
    product.name = name
    product.category_id = category_id
    product.category = _make_category()
    product.price = Decimal(price)
    product.discount_price = Decimal(discount_price) if discount_price else None
    product.stock = stock
    product.description = description
    product.embedding = None
    product.indexed_at = None
    return product


@pytest.fixture
def rag_service(monkeypatch: pytest.MonkeyPatch) -> RAGService:
    monkeypatch.setattr("app.services.rag_service.settings.GEMINI_API_KEY", "test-key")
    with patch("app.services.rag_service.genai.configure"):
        service = RAGService(MagicMock())
        service._vector_repo = MagicMock()
        return service


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.rag_service.settings.GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
        RAGService(MagicMock())


def test_embed_text_success(rag_service: RAGService) -> None:
    embedding = [0.1] * 768
    with patch(
        "app.services.rag_service.genai.embed_content",
        return_value={"embedding": embedding},
    ):
        result = rag_service._embed_text("hello", task_type="retrieval_query")

    assert result == embedding
    assert len(result) == 768


def test_embed_text_failure(rag_service: RAGService) -> None:
    with patch(
        "app.services.rag_service.genai.embed_content",
        side_effect=Exception("API error"),
    ):
        with pytest.raises(RuntimeError, match="Failed to generate embedding"):
            rag_service._embed_text("hello", task_type="retrieval_query")


def test_build_product_document_with_discount(rag_service: RAGService) -> None:
    product = _make_product(discount_price="80.00", price="100.00")
    stats = {
        1: CategoryStats(
            count=2,
            avg_price=Decimal("90.00"),
            min_price=Decimal("80.00"),
            max_price=Decimal("100.00"),
        )
    }

    document = rag_service._build_product_document(product, stats)

    assert "Discount price" in document
    assert "% off" in document


def test_build_product_document_low_stock(rag_service: RAGService) -> None:
    product = _make_product(stock=3)
    stats = {
        1: CategoryStats(
            count=1,
            avg_price=Decimal("100.00"),
            min_price=Decimal("100.00"),
            max_price=Decimal("100.00"),
        )
    }

    document = rag_service._build_product_document(product, stats)

    assert "LAST 3 UNITS" in document


def test_build_product_document_good_price(rag_service: RAGService) -> None:
    product = _make_product(discount_price="50.00", price="100.00")
    stats = {
        1: CategoryStats(
            count=3,
            avg_price=Decimal("90.00"),
            min_price=Decimal("50.00"),
            max_price=Decimal("120.00"),
        )
    }

    document = rag_service._build_product_document(product, stats)

    assert "Good price in its category" in document


def test_answer_query_no_results(rag_service: RAGService) -> None:
    rag_service._vector_repo.get_similar_products.return_value = []

    with patch(
        "app.services.rag_service.genai.embed_content",
        return_value={"embedding": [0.0] * 768},
    ):
        response = rag_service.answer_query("query with no matches")

    assert response.sources == []
    assert response.answer == NO_MATCH_ANSWER
    assert len(response.history) == 2


def test_answer_query_with_results(rag_service: RAGService) -> None:
    product_a = _make_product(1, name="Product A")
    product_b = _make_product(2, name="Product B")
    rag_service._vector_repo.get_similar_products.return_value = [
        (product_b, 0.7),
        (product_a, 0.9),
    ]
    rag_service._vector_repo.get_all_active_products.return_value = [
        product_a,
        product_b,
    ]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Mock answer")

    with patch(
        "app.services.rag_service.genai.embed_content",
        return_value={"embedding": [0.0] * 768},
    ), patch(
        "app.services.rag_service.genai.GenerativeModel",
        return_value=mock_model,
    ):
        response = rag_service.answer_query("find products")

    assert len(response.sources) == 2
    assert response.sources[0].similarity_score >= response.sources[1].similarity_score
    assert response.answer == "Mock answer"
    assert response.sources[0].name == "Product A"


def test_answer_query_with_history(rag_service: RAGService) -> None:
    product = _make_product()
    rag_service._vector_repo.get_similar_products.return_value = [(product, 0.8)]
    rag_service._vector_repo.get_all_active_products.return_value = [product]

    history = [
        RAGMessage(role="user", content="first question"),
        RAGMessage(role="assistant", content="first answer"),
    ]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Follow-up answer")

    with patch(
        "app.services.rag_service.genai.embed_content",
        return_value={"embedding": [0.0] * 768},
    ), patch(
        "app.services.rag_service.genai.GenerativeModel",
        return_value=mock_model,
    ):
        response = rag_service.answer_query("second question", history=history)

    assert len(response.history) == 4
    assert response.history[0].content == "first question"
    assert response.history[-1].role == "assistant"
    assert response.history[-1].content == "Follow-up answer"


def test_index_products_success(rag_service: RAGService) -> None:
    products = [_make_product(i) for i in range(1, 4)]
    rag_service._vector_repo.get_all_active_products.return_value = products

    with patch(
        "app.services.rag_service.genai.embed_content",
        return_value={"embedding": [0.2] * 768},
    ):
        result = rag_service.index_products()

    assert result == {"indexed": 3, "errors": 0}
    for product in products:
        assert product.embedding is not None
        assert product.indexed_at is not None
    rag_service.db.commit.assert_called()


def test_index_products_with_errors(rag_service: RAGService) -> None:
    products = [_make_product(i) for i in range(1, 4)]
    rag_service._vector_repo.get_all_active_products.return_value = products

    def embed_side_effect(*_args, **_kwargs):
        embed_side_effect.calls += 1
        if embed_side_effect.calls == 3:
            raise Exception("embed failed")
        return {"embedding": [0.3] * 768}

    embed_side_effect.calls = 0

    with patch(
        "app.services.rag_service.genai.embed_content",
        side_effect=embed_side_effect,
    ):
        result = rag_service.index_products()

    assert result == {"indexed": 2, "errors": 1}
    rag_service.db.commit.assert_called()
