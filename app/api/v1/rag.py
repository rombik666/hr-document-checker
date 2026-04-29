from fastapi import APIRouter

from app.rag.service import RagService
from app.schemas.rag import RagContext, RagSearchRequest, RagStatus


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagContext)
def search_rag_context(request: RagSearchRequest) -> RagContext:

    service = RagService()
    return service.search(request)


@router.get("/status", response_model=RagStatus)
def get_rag_status() -> RagStatus:
    """
    Возвращает технический статус RAG-подсистемы.
    """

    service = RagService()
    return service.get_status()