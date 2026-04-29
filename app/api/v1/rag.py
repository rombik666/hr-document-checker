from fastapi import APIRouter, Depends

from app.auth.dependencies import require_hr_or_admin
from app.db.models import UserORM
from app.rag.service import RagService
from app.schemas.rag import RagContext, RagSearchRequest, RagStatus


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagContext)
def search_rag_context(
    request: RagSearchRequest,
    current_user: UserORM = Depends(require_hr_or_admin),
) -> RagContext:

    service = RagService()
    return service.search(request)


@router.get("/status", response_model=RagStatus)
def get_rag_status(
    current_user: UserORM = Depends(require_hr_or_admin),
) -> RagStatus:

    service = RagService()
    return service.get_status()