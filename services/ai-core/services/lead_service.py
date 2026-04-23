"""
Lead Service — AI-powered lead classification and next-action suggestion.

Uses Claude directly (no RAG) because the input is the lead inquiry text itself
and the output is a structured classification.
Uses Pydantic to validate the structured output before persisting.
"""
import json
import time
import uuid
from typing import Any

import anthropic
import asyncpg
from pydantic import BaseModel

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.requests import ClassifyLeadRequest
from ..models.responses import ClassifyLeadResponse

log = get_logger(__name__)

_CLASSIFY_SYSTEM_PROMPT = """You are an intake coordinator at a wellness facility.
Analyse the lead inquiry and return a JSON object with exactly these fields:
{
  "intent": one of: "booking_inquiry" | "general_question" | "complaint" | "referral" | "other",
  "urgency": one of: "high" | "medium" | "low",
  "suggested_programme_ids": array of programme ids from the provided list (empty if none match),
  "budget_indicator": one of: "budget" | "mid" | "premium" | "unknown",
  "summary": a 1-2 sentence summary of the inquiry,
  "suggested_reply_draft": a warm, professional reply draft (2-3 paragraphs max)
}
Return ONLY the JSON object. No markdown, no explanation."""


class _ClassificationOutput(BaseModel):
    intent: str
    urgency: str
    suggested_programme_ids: list[str]
    budget_indicator: str
    summary: str
    suggested_reply_draft: str


class LeadService:
    def __init__(self, db_conn: asyncpg.Connection) -> None:
        self._conn = db_conn
        self._settings = get_settings()
        self._client = anthropic.AsyncAnthropic(
            api_key=self._settings.anthropic_api_key.get_secret_value()
        )

    async def classify_lead(
        self, request: ClassifyLeadRequest
    ) -> ClassifyLeadResponse:
        t_start = time.monotonic()

        programmes_context = "\n".join(
            f"- ID: {p['id']}, Name: {p['name']}: {p.get('description', '')[:200]}"
            for p in request.available_programmes[:20]
        )

        user_message = (
            f"Lead inquiry:\n{request.inquiry_text}\n\n"
            f"Available programmes:\n{programmes_context}"
        )

        response = await self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=1000,
            system=_CLASSIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text if response.content else "{}"

        try:
            parsed = _parse_classification_output(raw_text, request.available_programmes)
        except Exception as exc:
            log.warning(
                "lead.classify.parse_failed",
                error=str(exc),
                raw_preview=raw_text[:200],
            )
            parsed = _ClassificationOutput(
                intent="other",
                urgency="medium",
                suggested_programme_ids=[],
                budget_indicator="unknown",
                summary="Unable to parse inquiry automatically.",
                suggested_reply_draft="Thank you for your inquiry. A member of our team will be in touch shortly.",
            )

        latency_ms = int((time.monotonic() - t_start) * 1000)
        log.info(
            "lead.classify.completed",
            intent=parsed.intent,
            urgency=parsed.urgency,
            latency_ms=latency_ms,
        )

        return ClassifyLeadResponse(
            intent=parsed.intent,
            urgency=parsed.urgency,
            suggested_programme_ids=[
                uuid.UUID(pid) for pid in parsed.suggested_programme_ids
            ],
            budget_indicator=parsed.budget_indicator,
            summary=parsed.summary,
            suggested_reply_draft=parsed.suggested_reply_draft,
        )


def _parse_classification_output(
    raw_text: str, available_programmes: list[dict[str, Any]]
) -> _ClassificationOutput:
    """Parse and validate Claude's JSON output. Raises ValueError on invalid data."""
    available_ids = {str(p["id"]) for p in available_programmes}

    data = json.loads(raw_text)
    parsed = _ClassificationOutput.model_validate(data)

    # Validate that suggested programme IDs actually exist
    parsed.suggested_programme_ids = [
        pid for pid in parsed.suggested_programme_ids if pid in available_ids
    ]

    # Constrain enum-like fields to valid values
    if parsed.intent not in {
        "booking_inquiry", "general_question", "complaint", "referral", "other"
    }:
        parsed.intent = "other"
    if parsed.urgency not in {"high", "medium", "low"}:
        parsed.urgency = "medium"
    if parsed.budget_indicator not in {"budget", "mid", "premium", "unknown"}:
        parsed.budget_indicator = "unknown"

    return parsed
