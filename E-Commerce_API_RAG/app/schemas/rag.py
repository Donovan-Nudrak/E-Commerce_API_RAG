from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings


class RAGMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RAGQuery(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    history: list[RAGMessage] = Field(
        default_factory=list,
        max_length=settings.RAG_MAX_HISTORY,
    )


class RAGSource(BaseModel):
    id: int
    name: str
    price: Decimal
    discount_price: Decimal | None = None
    stock: int
    category_name: str
    similarity_score: float = 0.0

    model_config = {"from_attributes": True}


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    query: str
    history: list[RAGMessage]
