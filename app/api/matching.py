"""Internship matching HTTP endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.orchestrator import MatchingOrchestrator
from app.api.dependencies import get_matching_orchestrator
from app.auth.dependencies import get_current_user
from app.core.exceptions import (
    InvalidDocumentSelectionError,
    ResourceAccessDeniedError,
    ResourceNotFoundError,
)
from app.rag.exceptions import RAGError
from app.schemas.auth import UserPublic
from app.schemas.matching import MatchingRequest, MatchingResponse

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("", response_model=MatchingResponse)
async def match_internships(
    payload: MatchingRequest,
    current_user: UserPublic = Depends(get_current_user),
    orchestrator: MatchingOrchestrator = Depends(get_matching_orchestrator),
) -> MatchingResponse:
    """Retrieve cited internship matches for an authenticated user."""
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot match internships for another user",
        )
    try:
        return await orchestrator.match(payload)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidDocumentSelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RAGError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internship retrieval is temporarily unavailable",
        ) from exc
