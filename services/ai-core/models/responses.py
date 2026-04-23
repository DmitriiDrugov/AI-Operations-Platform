from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: UUID
    page_title: str
    section_heading: str | None
    similarity_score: float = Field(ge=0.0, le=1.0)
    source_url: str | None


class SuggestedAction(BaseModel):
    action_type: str
    label: str
    payload: dict


class CopilotQueryResponse(BaseModel):
    response_text: str
    citations: list[Citation]
    suggested_actions: list[SuggestedAction]
    interaction_id: UUID
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class KnowledgeChunkResult(BaseModel):
    chunk_id: UUID
    page_title: str
    section_heading: str | None
    content_text: str
    source_url: str | None
    similarity_score: float
    source_type: str


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeChunkResult]
    query_embedding_latency_ms: int
    search_latency_ms: int


class ClassifyLeadResponse(BaseModel):
    intent: str
    urgency: str
    suggested_programme_ids: list[UUID]
    budget_indicator: str
    summary: str
    suggested_reply_draft: str


class GuestSummaryResponse(BaseModel):
    guest_name: str
    summary: str
    key_notes: list[str]
    upcoming_appointments: list[dict]
    package_status: dict | None
    interaction_id: UUID
    model: str
    latency_ms: int


class DraftMessageResponse(BaseModel):
    draft_text: str
    subject: str | None
    interaction_id: UUID
    model: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, bool]
