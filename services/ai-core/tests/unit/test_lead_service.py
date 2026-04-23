"""
Unit tests for LeadService — mocks Claude API, tests classification parsing and sanitisation.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_core.models.requests import ClassifyLeadRequest
from ai_core.services.lead_service import LeadService, _parse_classification_output


@pytest.fixture
def sample_programmes() -> list[dict]:
    return [
        {"id": str(uuid.uuid4()), "name": "7-Day Detox Retreat", "description": "Full body detox programme"},
        {"id": str(uuid.uuid4()), "name": "Weekend Recharge", "description": "2-night stress relief"},
    ]


@pytest.fixture
def mock_db_conn() -> AsyncMock:
    return AsyncMock()


class TestParseClassificationOutput:
    def test_valid_json_parses_correctly(self, sample_programmes: list[dict]) -> None:
        programme_id = sample_programmes[0]["id"]
        raw = json.dumps({
            "intent": "booking_inquiry",
            "urgency": "high",
            "suggested_programme_ids": [programme_id],
            "budget_indicator": "premium",
            "summary": "Guest wants to book the detox retreat urgently.",
            "suggested_reply_draft": "Thank you for reaching out...",
        })
        result = _parse_classification_output(raw, sample_programmes)
        assert result.intent == "booking_inquiry"
        assert result.urgency == "high"
        assert programme_id in result.suggested_programme_ids

    def test_unknown_programme_id_is_filtered(self, sample_programmes: list[dict]) -> None:
        raw = json.dumps({
            "intent": "booking_inquiry",
            "urgency": "medium",
            "suggested_programme_ids": [str(uuid.uuid4())],  # unknown id
            "budget_indicator": "unknown",
            "summary": "Some inquiry",
            "suggested_reply_draft": "Reply...",
        })
        result = _parse_classification_output(raw, sample_programmes)
        assert result.suggested_programme_ids == []

    def test_invalid_intent_defaults_to_other(self, sample_programmes: list[dict]) -> None:
        raw = json.dumps({
            "intent": "INVALID_INTENT",
            "urgency": "medium",
            "suggested_programme_ids": [],
            "budget_indicator": "unknown",
            "summary": "Summary",
            "suggested_reply_draft": "Reply",
        })
        result = _parse_classification_output(raw, sample_programmes)
        assert result.intent == "other"

    def test_invalid_json_raises_value_error(self, sample_programmes: list[dict]) -> None:
        with pytest.raises(Exception):
            _parse_classification_output("not valid json", sample_programmes)


class TestClassifyLeadRequest:
    def test_inquiry_text_is_sanitised(self) -> None:
        request = ClassifyLeadRequest(
            inquiry_text="Hello\x00 \x01world\nI want to book.",
            organisation_id=str(uuid.uuid4()),
            available_programmes=[],
        )
        assert "\x00" not in request.inquiry_text
        assert "\x01" not in request.inquiry_text
        assert "I want to book" in request.inquiry_text

    def test_inquiry_text_is_truncated_at_5000_chars(self) -> None:
        long_text = "A" * 6000
        request = ClassifyLeadRequest(
            inquiry_text=long_text,
            organisation_id=str(uuid.uuid4()),
            available_programmes=[],
        )
        assert len(request.inquiry_text) <= 5000
