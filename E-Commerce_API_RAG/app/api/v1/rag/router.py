from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import require_admin
from app.core.limiter import limiter
from app.database.session import get_db
from app.schemas.rag import RAGQuery, RAGResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


def _rag_runtime_error_to_http(exc: RuntimeError) -> HTTPException:
    message = str(exc).lower()

    if "timed out" in message:
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The request to the AI service timed out. Please try again.",
        )
    if "quota" in message or "rate" in message:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI service rate limit was exceeded. Please try again later.",
        )
    if "not configured" in message:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured",
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred while processing your request.",
    )


def _rag_index_runtime_error_to_http(exc: RuntimeError) -> HTTPException:
    message = str(exc).lower()
    if "run /rag/index before" in message:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return _rag_runtime_error_to_http(exc)


@router.post("/query", response_model=RAGResponse)
@limiter.limit("20/minute")
def query(
    request: Request,
    data: RAGQuery,
    db: Session = Depends(get_db),
) -> RAGResponse:
    try:
        service = RAGService(db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured",
        )

    try:
        return service.answer_query(data.query, data.history)
    except RuntimeError as exc:
        raise _rag_runtime_error_to_http(exc) from exc


@router.post("/index", dependencies=[Depends(require_admin)])
def index(db: Session = Depends(get_db)) -> dict:
    try:
        service = RAGService(db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured",
        )

    result = service.index_products()
    return {
        "indexed": result["indexed"],
        "errors": result["errors"],
        "message": "Reindexed active products.",
    }


@router.post("/index/categories", dependencies=[Depends(require_admin)])
def index_categories(db: Session = Depends(get_db)) -> dict:
    try:
        service = RAGService(db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured",
        )

    try:
        return service.index_categories_context()
    except RuntimeError as exc:
        raise _rag_index_runtime_error_to_http(exc) from exc


@router.put(
    "/products/{product_id}/reindex",
    dependencies=[Depends(require_admin)],
)
def reindex_product(product_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        service = RAGService(db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not configured",
        )

    if not service.reindex_product(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive.",
        )

    return {"reindexed": True, "product_id": product_id}
