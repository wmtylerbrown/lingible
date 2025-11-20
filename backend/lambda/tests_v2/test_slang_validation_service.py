from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from models.config import LLMConfig, SlangValidationConfig
from models.slang import (
    ApprovalStatus,
    LLMValidationEvidence,
    LLMValidationResult,
    SlangSubmission,
    SlangSubmissionStatus,
    SubmissionContext,
)
from services.slang_validation_service import SlangValidationService


def _config() -> tuple[SlangValidationConfig, LLMConfig]:
    return (
        SlangValidationConfig(
            auto_approval_enabled=True,
            auto_approval_threshold=0.8,
            web_search_enabled=True,
            max_search_results=3,
            tavily_api_key="key",
        ),
        LLMConfig(
            lexicon_s3_bucket="bucket",
            lexicon_s3_key="key",
            model="anthropic",
            max_tokens=2000,
            temperature=0.2,
            top_p=0.9,
            low_confidence_threshold=0.5,
            age_max_rating="E",
            age_filter_mode="skip",
        ),
    )


def _submission(term: str = "rizz") -> SlangSubmission:
    return SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term=term,
        meaning="meaning",
        example_usage="usage",
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
        status=ApprovalStatus.PENDING,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        reviewed_at=None,
        reviewed_by=None,
        llm_validation_status=SlangSubmissionStatus.PENDING_VALIDATION,
        llm_confidence_score=None,
        llm_validation_result=None,
        approval_type=None,
        approved_by=None,
        upvotes=0,
        upvoted_by=[],
    )


def _service() -> SlangValidationService:
    service = SlangValidationService.__new__(SlangValidationService)
    validation_config, llm_config = _config()
    service.config_service = Mock()
    service.validation_config = validation_config
    service.llm_config = llm_config
    service.bedrock_client = Mock()
    return service


def test_validate_submission_success() -> None:
    service = _service()
    service._web_search = Mock(return_value=[{"title": "result", "content": "usage"}])
    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[LLMValidationEvidence(source="web", example="usage")],
        recommended_definition=None,
        usage_score=8,
        validated_at=datetime.now(timezone.utc),
    )
    service._call_claude = Mock(return_value=result)

    response = service.validate_submission(_submission())

    assert response.is_valid is True
    service._call_claude.assert_called_once()


def test_validate_submission_fallback_on_exception() -> None:
    service = _service()
    service._web_search = Mock(return_value=[])
    service._call_claude = Mock(side_effect=RuntimeError("boom"))
    fallback = service.validate_submission(_submission())
    assert fallback.confidence == Decimal("0.5")


def test_web_search_returns_empty_on_error() -> None:
    service = _service()
    service.validation_config.tavily_api_key = "key"
    with patch("services.slang_validation_service.TavilyClient") as tavily_cls:
        tavily_cls.return_value.search.side_effect = RuntimeError("boom")
        results = service._web_search("term")
    assert results == []


def test_parse_llm_response_handles_markdown() -> None:
    service = _service()
    payload = """```json
{"is_valid": true, "confidence": 0.9, "usage_score": 8, "evidence": [{"source": "web", "example": "usage"}]}
```"""
    result = service._parse_llm_response(payload, _submission())
    assert result.is_valid is True


def test_parse_llm_response_fallback_on_error() -> None:
    service = _service()
    result = service._parse_llm_response("not json", _submission())
    assert result.confidence == Decimal("0.5")


def test_should_auto_approve_uses_threshold() -> None:
    service = _service()
    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[],
        recommended_definition=None,
        usage_score=8,
        validated_at=datetime.now(timezone.utc),
    )
    assert service.should_auto_approve(result) is True


def test_should_auto_approve_respects_flag() -> None:
    service = _service()
    service.validation_config.auto_approval_enabled = False
    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[],
        recommended_definition=None,
        usage_score=8,
        validated_at=datetime.now(timezone.utc),
    )
    assert service.should_auto_approve(result) is False


def test_call_claude_parses_response_body() -> None:
    service = _service()
    body = {
        "content": [
            {
                "text": json.dumps(
                    {
                        "is_valid": True,
                        "confidence": 0.88,
                        "usage_score": 7,
                        "evidence": [{"source": "web", "example": "usage"}],
                    }
                )
            }
        ]
    }

    class _Body:
        def read(self) -> bytes:
            return json.dumps(body).encode("utf-8")

    service.bedrock_client.invoke_model.return_value = {"body": _Body()}
    result = service._call_claude(_submission(), [])
    assert result.confidence == Decimal("0.88")
    service.bedrock_client.invoke_model.assert_called_once()


def test_call_claude_raises_on_failure() -> None:
    service = _service()
    service.bedrock_client.invoke_model.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        service._call_claude(_submission(), [])


def test_create_validation_prompt_includes_web_results() -> None:
    service = _service()
    prompt = service._create_validation_prompt(
        _submission(),
        [
            {"title": "Urban", "url": "https://example.com", "content": "definition"},
        ],
    )
    assert "Urban" in prompt
    assert "WEB SEARCH RESULTS" in prompt


def test_create_validation_prompt_handles_empty_results() -> None:
    service = _service()
    prompt = service._create_validation_prompt(_submission(), [])
    assert "No results available" in prompt


def test_web_search_success_path() -> None:
    service = _service()
    service.validation_config.tavily_api_key = "key"
    with patch("services.slang_validation_service.TavilyClient") as tavily_cls:
        tavily_cls.return_value.search.return_value = {
            "results": [{"title": "result", "content": "usage", "url": "x"}],
            "response_time": 1.2,
        }
        results = service._web_search("term")
    assert len(results) == 1


def test_fallback_validation_marks_manual_review() -> None:
    service = _service()
    result = service._fallback_validation(_submission())
    assert result.evidence[0].source == "fallback"


def test_determine_status_paths() -> None:
    service = _service()
    approved = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.95"),
        evidence=[],
        recommended_definition=None,
        usage_score=9,
        validated_at=datetime.now(timezone.utc),
    )
    service.validation_config.auto_approval_threshold = 0.8
    assert service.determine_status(approved) is SlangSubmissionStatus.AUTO_APPROVED

    rejected = approved.model_copy(update={"is_valid": False})
    assert service.determine_status(rejected) is SlangSubmissionStatus.REJECTED

    pending = approved.model_copy(update={"usage_score": 3})
    assert service.determine_status(pending) is SlangSubmissionStatus.VALIDATED
