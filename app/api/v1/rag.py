from fastapi import APIRouter

from app.rag.service import RagService
from app.schemas.rag import RagContext, RagSearchRequest


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagContext)
def search_rag_context(request: RagSearchRequest) -> RagContext:
    """
    Поиск релевантного контекста в базе знаний.

    """

    service = RagService()
    return service.search(request)