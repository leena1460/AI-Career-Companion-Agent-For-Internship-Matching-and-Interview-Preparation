"""Request and response schemas for internship matching."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.rag import InternshipJob


class MatchingRequest(BaseModel):
    """User context and optional resume-field overrides for matching."""

    user_id: uuid.UUID
    user_detail_id: uuid.UUID | None = None
    education: list[dict[str, object]] | None = None
    skills: list[str] | None = None
    projects: list[dict[str, object]] | None = None
    experience: list[dict[str, object]] | None = None
    profile_summary: str | None = None
    certifications: list[dict[str, object]] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class MatchingProfile(BaseModel):
    """Resolved profile used to construct the RAG query."""

    user_id: uuid.UUID
    name: str
    email: str
    location_preference: str | None = None
    education: list[dict[str, object]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[dict[str, object]] = Field(default_factory=list)
    experience: list[dict[str, object]] = Field(default_factory=list)
    profile_summary: str = ""
    certifications: list[dict[str, object]] = Field(default_factory=list)


class MatchCitation(BaseModel):
    """Source attribution for a retrieved internship."""

    source: str
    apply_url: str
    vector_document_id: str


class JobMatch(BaseModel):
    """Ranked internship result with retrieval score and citation."""

    score: float
    job: InternshipJob | None
    citation: MatchCitation


class MatchingResponse(BaseModel):
    """Resolved matching profile and ranked internship results."""

    profile: MatchingProfile
    matches: list[JobMatch]
