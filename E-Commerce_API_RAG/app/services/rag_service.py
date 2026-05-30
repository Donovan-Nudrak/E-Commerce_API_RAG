import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import NoReturn

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.product import Product
from app.repositories.vector_repository import VectorRepository
from app.schemas.rag import RAGMessage, RAGResponse, RAGSource

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert sales assistant for an online store. "
    "Always respond in the same language as the customer's latest message.\n"
    "Rules:\n"
    "- Use ONLY products from the context to answer. Never invent products or prices.\n"
    "- If the question is about price, always mention the discounted price when one exists.\n"
    "- If several products are relevant, list them briefly with name and price.\n"
    "- If no products are relevant, say so honestly and suggest rephrasing the search.\n"
    "- Be concise: at most 3-4 sentences or a short list."
)

NO_MATCH_ANSWER = (
    "I did not find relevant products for your query. "
    "Try rephrasing your search with different terms."
)

PRODUCT_EMBED_WEIGHT = 0.8
HISTORY_MAX_MESSAGES = 6


@dataclass
class CategoryStats:
    count: int
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal


class RAGService:

    def __init__(self, db: Session) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.db = db
        self._vector_repo = VectorRepository(db)
        self._embedding_model = settings.RAG_EMBEDDING_MODEL
        self._embedding_dim = settings.RAG_EMBEDDING_DIM
        self._generation_model = settings.RAG_GENERATION_MODEL
        self._top_k = settings.RAG_TOP_K

    @staticmethod
    def _request_options() -> dict:
        return {"timeout": settings.RAG_GEMINI_TIMEOUT}

    @staticmethod
    def _handle_gemini_exception(exc: Exception, operation: str) -> NoReturn:
        if isinstance(exc, google_exceptions.DeadlineExceeded):
            raise RuntimeError("Gemini request timed out") from exc
        if isinstance(exc, google_exceptions.ResourceExhausted):
            raise RuntimeError("Gemini API quota exceeded") from exc
        if isinstance(exc, google_exceptions.TooManyRequests):
            raise RuntimeError("Gemini API rate limit exceeded") from exc

        logger.error("Gemini %s failed: %s", operation, exc)
        raise RuntimeError(f"Failed to {operation}") from exc

    def _embed_text(self, text: str, task_type: str) -> list[float]:
        try:
            result = genai.embed_content(
                model=self._embedding_model,
                content=text,
                task_type=task_type,
                output_dimensionality=self._embedding_dim,
                request_options=self._request_options(),
            )
        except Exception as exc:
            self._handle_gemini_exception(exc, "generate embedding")

        return result["embedding"]

    @staticmethod
    def _effective_price(product: Product) -> Decimal:
        if product.discount_price is not None:
            return product.discount_price
        return product.price

    @staticmethod
    def _discount_percent(price: Decimal, discount_price: Decimal) -> int:
        return int((1 - discount_price / price) * 100)

    @staticmethod
    def _build_category_stats_map(products: list[Product]) -> dict[int, CategoryStats]:
        totals: dict[int, list[Decimal]] = {}
        for product in products:
            effective = RAGService._effective_price(product)
            totals.setdefault(product.category_id, []).append(effective)

        return {
            category_id: CategoryStats(
                count=len(prices),
                avg_price=sum(prices) / len(prices),
                min_price=min(prices),
                max_price=max(prices),
            )
            for category_id, prices in totals.items()
        }

    @staticmethod
    def _blend_embeddings(
        product_embedding: list[float],
        category_embedding: list[float],
        product_weight: float = PRODUCT_EMBED_WEIGHT,
    ) -> list[float]:
        category_weight = 1.0 - product_weight
        return [
            product_weight * product_value + category_weight * category_value
            for product_value, category_value in zip(
                product_embedding, category_embedding
            )
        ]

    @staticmethod
    def _build_category_document(
        name: str,
        count: int,
        min_price: Decimal,
        max_price: Decimal,
    ) -> str:
        return (
            f"Category: {name}. Available products: {count}. "
            f"Price range: from ${min_price} to ${max_price}."
        )

    def _resolve_category_stats(
        self,
        category_stats: dict[int, CategoryStats] | None,
    ) -> dict[int, CategoryStats]:
        if category_stats is not None:
            return category_stats
        products = self._vector_repo.get_all_active_products()
        return self._build_category_stats_map(products)

    def _build_product_document(
        self,
        product: Product,
        category_stats: dict[int, CategoryStats] | None = None,
    ) -> str:
        stats_map = self._resolve_category_stats(category_stats)
        category_id = product.category_id
        stats = stats_map.get(category_id)
        if stats is None:
            count = self._vector_repo.get_category_product_count(category_id)
        else:
            count = stats.count

        document = (
            f"Product: {product.name}. "
            f"Category: {product.category.name} ({count} products available). "
            f"Description: {product.description}. "
            f"Price: ${product.price}. "
            f"Stock available: {product.stock} units."
        )

        if stats is not None:
            effective_price = self._effective_price(product)
            if effective_price <= stats.avg_price:
                document += " Good price in its category."

        if product.discount_price is not None and product.price > 0:
            pct = self._discount_percent(product.price, product.discount_price)
            document += (
                f" Original price: ${product.price}. "
                f"Discount price: ${product.discount_price} ({pct}% off)."
            )
        if product.stock <= 5:
            document += f" LAST {product.stock} UNITS."
        return document

    def _build_context(
        self,
        products: list[Product],
        category_stats: dict[int, CategoryStats] | None = None,
    ) -> str:
        stats_map = self._resolve_category_stats(category_stats)
        documents = [
            f"{index}. {self._build_product_document(product, stats_map)}"
            for index, product in enumerate(products, start=1)
        ]
        return "\n\n".join(documents)

    @staticmethod
    def _format_history(messages: list[RAGMessage]) -> str:
        lines = []
        for message in messages:
            label = "User" if message.role == "user" else "Assistant"
            lines.append(f"{label}: {message.content}")
        return "\n".join(lines)

    @staticmethod
    def _build_updated_history(
        history: list[RAGMessage], query: str, answer: str
    ) -> list[RAGMessage]:
        return history + [
            RAGMessage(role="user", content=query),
            RAGMessage(role="assistant", content=answer),
        ]

    def _build_prompt(
        self, query: str, context: str, history: list[RAGMessage]
    ) -> str:
        parts = [SYSTEM_PROMPT]

        recent_history = history[-HISTORY_MAX_MESSAGES:]
        if recent_history:
            parts.append(
                f"Previous conversation:\n{self._format_history(recent_history)}"
            )

        parts.append(f"Context:\n{context}")
        parts.append(f"Customer question:\n{query}")
        return "\n\n".join(parts)

    @staticmethod
    def _to_rag_source(product: Product, similarity_score: float) -> RAGSource:
        return RAGSource(
            id=product.id,
            name=product.name,
            price=product.price,
            discount_price=product.discount_price,
            stock=product.stock,
            category_name=product.category.name,
            similarity_score=similarity_score,
        )

    def answer_query(
        self, query: str, history: list[RAGMessage] | None = None
    ) -> RAGResponse:
        history = history or []
        embedding = self._embed_text(query, task_type="retrieval_query")
        candidates = self._top_k * settings.RAG_CANDIDATE_MULTIPLIER
        ranked = self._vector_repo.get_similar_products(embedding, candidates)

        filtered = [
            (product, score)
            for product, score in ranked
            if score >= settings.RAG_SIMILARITY_THRESHOLD
        ]
        filtered.sort(key=lambda item: item[1], reverse=True)
        products_with_scores = filtered[: self._top_k]

        if not products_with_scores:
            return RAGResponse(
                answer=NO_MATCH_ANSWER,
                sources=[],
                query=query,
                history=self._build_updated_history(
                    history, query, NO_MATCH_ANSWER
                ),
            )

        products = [product for product, _ in products_with_scores]
        category_stats = self._build_category_stats_map(
            self._vector_repo.get_all_active_products()
        )
        context = self._build_context(products, category_stats)
        prompt = self._build_prompt(query, context, history)

        try:
            model = genai.GenerativeModel(self._generation_model)
            response = model.generate_content(
                prompt,
                request_options=self._request_options(),
            )
        except Exception as exc:
            self._handle_gemini_exception(exc, "generate answer")

        sources = [
            self._to_rag_source(product, score)
            for product, score in products_with_scores
        ]
        answer = response.text

        return RAGResponse(
            answer=answer,
            sources=sources,
            query=query,
            history=self._build_updated_history(history, query, answer),
        )

    def index_products(self) -> dict:
        products = self._vector_repo.get_all_active_products()
        category_stats = self._build_category_stats_map(products)
        indexed = 0
        errors = 0

        for product in products:
            try:
                document = self._build_product_document(product, category_stats)
                product.embedding = self._embed_text(
                    document, task_type="retrieval_document"
                )
                product.indexed_at = datetime.now(timezone.utc)
                indexed += 1
                if indexed % settings.RAG_COMMIT_BATCH_SIZE == 0:
                    self.db.commit()
            except Exception as exc:
                logger.error(
                    "Failed to index product %s: %s", product.id, exc
                )
                errors += 1

        self.db.commit()
        return {"indexed": indexed, "errors": errors}

    def index_categories_context(self) -> dict:
        if self._vector_repo.count_active_without_indexed_at() > 0:
            raise RuntimeError("Run /rag/index before /rag/index/categories")

        products = self._vector_repo.get_all_active_products()
        category_stats = self._build_category_stats_map(products)
        categories_processed = 0
        products_updated = 0
        errors = 0

        for category_id, stats in category_stats.items():
            try:
                category_products = self._vector_repo.get_products_by_category(
                    category_id
                )
                if not category_products:
                    continue

                category_name = category_products[0].category.name
                document = self._build_category_document(
                    category_name,
                    stats.count,
                    stats.min_price,
                    stats.max_price,
                )
                category_embedding = self._embed_text(
                    document, task_type="retrieval_document"
                )

                for product in category_products:
                    if product.embedding is None:
                        logger.error(
                            "Product %s has no embedding, run /rag/index first",
                            product.id,
                        )
                        errors += 1
                        continue

                    product.embedding = self._blend_embeddings(
                        list(product.embedding), category_embedding
                    )
                    products_updated += 1
                    if products_updated % settings.RAG_COMMIT_BATCH_SIZE == 0:
                        self.db.commit()

                categories_processed += 1
            except Exception as exc:
                logger.error(
                    "Failed to index category %s: %s", category_id, exc
                )
                errors += 1

        self.db.commit()
        return {
            "categories_processed": categories_processed,
            "products_updated": products_updated,
            "errors": errors,
        }

    def reindex_product(self, product_id: int) -> bool:
        """Re-embed a single active product (base embedding, no category blend)."""
        product = (
            self.db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.id == product_id)
            .first()
        )
        if not product or not product.is_active:
            return False

        try:
            category_stats = self._build_category_stats_map(
                self._vector_repo.get_all_active_products()
            )
            document = self._build_product_document(product, category_stats)
            product.embedding = self._embed_text(
                document, task_type="retrieval_document"
            )
            product.indexed_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        except Exception as exc:
            logger.warning("Failed to reindex product %s: %s", product_id, exc)
            self.db.rollback()
            return False
