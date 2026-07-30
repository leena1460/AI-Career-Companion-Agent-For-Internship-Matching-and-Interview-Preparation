"""Resume, cover-letter, and profile-summary HTTP endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.dependencies import get_profile_service, get_user_detail_service
from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DocumentParsingError,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidDocumentError,
    ResourceNotFoundError,
    UnsupportedDocumentTypeError,
)
from app.schemas.auth import UserPublic
from app.schemas.user_detail import (
    ParsedCoverLetterResponse,
    ParsedResumeResponse,
    ProfileSummaryResponse,
)
from app.services.profile_service import ProfileService
from app.services.user_detail_service import UserDetailService

router = APIRouter(prefix="/users", tags=["user documents"])


def _authorize_user(user_id: UUID, current_user: UserPublic) -> None:
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another user's documents",
        )


async def _read_upload(file: UploadFile, settings: Settings) -> bytes:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    try:
        return await file.read(max_bytes + 1)
    finally:
        await file.close()


def _raise_document_http_error(exc: Exception) -> None:
    if isinstance(exc, DocumentTooLargeError):
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc))
    if isinstance(exc, UnsupportedDocumentTypeError):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        )
    if isinstance(exc, (EmptyDocumentError, InvalidDocumentError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    if isinstance(exc, DocumentParsingError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    raise exc


@router.post(
    "/{user_id}/resumes/parse",
    response_model=ParsedResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def parse_resume(
    user_id: UUID,
    file: UploadFile,
    current_user: UserPublic = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    service: UserDetailService = Depends(get_user_detail_service),
) -> ParsedResumeResponse:
    """Parse and save an authenticated user's PDF or DOCX resume."""
    _authorize_user(user_id, current_user)
    file_name = file.filename or ""
    content = await _read_upload(file, settings)
    try:
        return await service.parse_resume(user_id, file_name, content)
    except (
        DocumentParsingError,
        DocumentTooLargeError,
        EmptyDocumentError,
        InvalidDocumentError,
        UnsupportedDocumentTypeError,
    ) as exc:
        _raise_document_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/{user_id}/resumes", response_model=list[ParsedResumeResponse])
async def list_resumes(
    user_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    service: UserDetailService = Depends(get_user_detail_service),
) -> list[ParsedResumeResponse]:
    """List the authenticated user's parsed resumes."""
    _authorize_user(user_id, current_user)
    return await service.list_resumes(user_id)


@router.post(
    "/{user_id}/cover-letters/parse",
    response_model=ParsedCoverLetterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def parse_cover_letter(
    user_id: UUID,
    file: UploadFile,
    current_user: UserPublic = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    service: UserDetailService = Depends(get_user_detail_service),
) -> ParsedCoverLetterResponse:
    """Parse and save an authenticated user's PDF or DOCX cover letter."""
    _authorize_user(user_id, current_user)
    file_name = file.filename or ""
    content = await _read_upload(file, settings)
    try:
        return await service.parse_cover_letter(user_id, file_name, content)
    except (
        DocumentParsingError,
        DocumentTooLargeError,
        EmptyDocumentError,
        InvalidDocumentError,
        UnsupportedDocumentTypeError,
    ) as exc:
        _raise_document_http_error(exc)
        raise AssertionError("unreachable")


@router.get(
    "/{user_id}/cover-letters",
    response_model=list[ParsedCoverLetterResponse],
)
async def list_cover_letters(
    user_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    service: UserDetailService = Depends(get_user_detail_service),
) -> list[ParsedCoverLetterResponse]:
    """List the authenticated user's parsed cover letters."""
    _authorize_user(user_id, current_user)
    return await service.list_cover_letters(user_id)


@router.post("/{user_id}/profile-summary", response_model=ProfileSummaryResponse)
async def create_profile_summary(
    user_id: UUID,
    current_user: UserPublic = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileSummaryResponse:
    """Create a matching-ready summary from user and profile data."""
    _authorize_user(user_id, current_user)
    try:
        return await service.create_summary(user_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
