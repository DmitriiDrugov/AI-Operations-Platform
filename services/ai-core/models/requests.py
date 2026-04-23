from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class InteractionType(StrEnum):
    GENERAL = "general"
    GUEST_SUMMARY = "guest_summary"
    SOP_LOOKUP = "sop_lookup"
    BILLING_QUERY = "billing_query"
    DRAFT_MESSAGE = "draft_message"
    CLINICAL_SUMMARY = "clinical_summary"


class CopilotContext(BaseModel):
    guest_id: UUID | None = None
    stay_id: UUID | None = None
    interaction_type: InteractionType = InteractionType.GENERAL


class CopilotQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    context: CopilotContext
    organisation_id: UUID
    user_id: UUID

    @field_validator("query")
    @classmethod
    def sanitise_query(cls, v: str) -> str:
        # Strip null bytes and control characters that could affect prompt structure
        sanitised = "".join(
            ch for ch in v if ch.isprintable() or ch in ("\n", "\t")
        )
        return sanitised[:2000]


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    organisation_id: UUID
    source_types: list[str] | None = None
    limit: int = Field(default=8, ge=1, le=20)
    min_similarity: float = Field(default=0.72, ge=0.0, le=1.0)


class ClassifyLeadRequest(BaseModel):
    inquiry_text: str = Field(min_length=1, max_length=5000)
    organisation_id: UUID
    available_programmes: list[dict[str, Any]] = Field(max_length=50)

    @field_validator("inquiry_text")
    @classmethod
    def sanitise_inquiry(cls, v: str) -> str:
        return "".join(
            ch for ch in v if ch.isprintable() or ch in ("\n", "\t")
        )[:5000]


class SummariseGuestRequest(BaseModel):
    guest_id: UUID
    organisation_id: UUID
    user_id: UUID
    include_clinical: bool = False


class DraftMessageRequest(BaseModel):
    guest_id: UUID
    organisation_id: UUID
    user_id: UUID
    context_type: str = Field(description="booking_confirmation | follow_up | welcome | custom")
    custom_instruction: str | None = Field(default=None, max_length=500)
    tone: str = Field(default="warm_professional", description="warm_professional | formal | casual")
