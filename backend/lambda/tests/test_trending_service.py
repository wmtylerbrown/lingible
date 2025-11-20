from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from models.trending import (
    TrendingCategory,
    TrendingJobRequest,
    TrendingTerm,
    TrendingTermResponse,
    TrendingListResponse,
    TrendingJobResponse,
)
from models.users import UserTier
from services.trending_service import TrendingService
from utils.exceptions import ValidationError
from utils.response import create_model_response


def _service() -> tuple[TrendingService, Mock, Mock]:
    service = TrendingService.__new__(TrendingService)
    service.repository = Mock()
    service.config_service = Mock()
    service.bedrock_client = Mock()
    service.llm_config = SimpleNamespace(model="model")
    service.user_service = Mock()
    return service, service.repository, service.user_service


def _term(name: str = "rizz") -> TrendingTerm:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return TrendingTerm(
        term=name,
        definition="charisma",
        category=TrendingCategory.SLANG,
        popularity_score=Decimal("50"),
        search_count=10,
        translation_count=5,
        first_seen=now,
        last_updated=now,
        is_active=True,
        example_usage="he's got rizz",
        origin="internet",
        related_terms=["charisma"],
    )


def test_get_trending_terms_free_tier_restrictions() -> None:
    service, repository, user_service = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.FREE)
    repository.get_trending_terms.return_value = [_term()]
    repository.get_trending_stats.return_value = {"total_active_terms": 1}

    response = service.get_trending_terms("user-1", limit=30)
    assert len(response.terms) == 1

    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.FREE)
    with pytest.raises(ValidationError):
        service.get_trending_terms(
            "user-1", limit=5, category=TrendingCategory.MEME
        )


def test_get_trending_terms_premium_limit_validation() -> None:
    service, _, user_service = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    with pytest.raises(ValidationError):
        service.get_trending_terms("user", limit=101)


def test_create_trending_term_rejects_duplicates() -> None:
    service, repository, _ = _service()
    repository.get_trending_term.return_value = _term()
    with pytest.raises(ValidationError):
        service.create_trending_term(
            "rizz", "charisma", TrendingCategory.SLANG, Decimal("10")
        )


def test_update_trending_term_missing() -> None:
    service, repository, _ = _service()
    repository.get_trending_term.return_value = None
    with pytest.raises(ValidationError):
        service.update_trending_term("unknown", definition="new")


def test_run_trending_job_success_updates_counts() -> None:
    service, repository, _ = _service()
    service._generate_trending_terms_with_bedrock = Mock(
        return_value=[
            {
                "term": "new",
                "definition": "def",
                "category": TrendingCategory.SLANG,
                "popularity_score": Decimal("80"),
                "example_usage": "example",
                "origin": "origin",
                "related_terms": [],
            }
        ]
    )
    repository.get_trending_term.return_value = None
    repository.create_trending_term.return_value = True

    response = service.run_trending_job(
        TrendingJobRequest(job_type="gen_z_slang_analysis", source="bedrock")
    )
    assert response.status == "completed"
    repository.create_trending_term.assert_called_once()


def test_run_trending_job_handles_errors() -> None:
    service, repository, _ = _service()
    service._generate_trending_terms_with_bedrock = Mock(side_effect=RuntimeError("boom"))
    response = service.run_trending_job(
        TrendingJobRequest(job_type="gen_z_slang_analysis", source="bedrock")
    )
    assert response.status == "failed"


def test_parse_bedrock_response_fallback_on_invalid_json() -> None:
    service, _, _ = _service()
    result = service._parse_bedrock_trending_response("not json")
    assert len(result) > 0  # fallback terms


def test_generate_trending_terms_with_bedrock_handles_exception() -> None:
    service, _, _ = _service()
    service._call_bedrock_for_trending_terms = Mock(side_effect=RuntimeError("boom"))
    terms = service._generate_trending_terms_with_bedrock()
    assert len(terms) > 0


def test_trending_term_response_serialization_matches_api_contract() -> None:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    response = TrendingTermResponse(
        term="rizz",
        definition="charisma",
        category=TrendingCategory.SLANG,
        popularity_score=Decimal("88.5"),
        search_count=120,
        translation_count=45,
        first_seen=now,
        last_updated=now,
        is_active=True,
        example_usage="he's got rizz",
        origin="Gen Z",
        related_terms=["charisma", "confidence"],
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["term"] == "rizz"
    assert body["category"] == TrendingCategory.SLANG.value
    assert isinstance(body["popularity_score"], float)
    datetime.fromisoformat(body["first_seen"])
    assert body["related_terms"] == ["charisma", "confidence"]


def test_trending_list_response_serialization_matches_api_contract() -> None:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    term_response = TrendingTermResponse(
        term="bet",
        definition="agreement",
        category=TrendingCategory.EXPRESSION,
        popularity_score=Decimal("70"),
        search_count=50,
        translation_count=25,
        first_seen=now,
        last_updated=now,
        is_active=True,
        example_usage="Bet, see you there.",
        origin="Atlanta",
        related_terms=["sure"],
    )
    response = TrendingListResponse(
        terms=[term_response],
        total_count=1,
        last_updated=now,
        category_filter=TrendingCategory.EXPRESSION,
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["total_count"] == 1
    assert body["category_filter"] == TrendingCategory.EXPRESSION.value
    assert body["terms"][0]["term"] == "bet"


def test_trending_job_response_serialization_matches_api_contract() -> None:
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    response = TrendingJobResponse(
        job_id="job-123",
        status="completed",
        terms_processed=100,
        terms_added=20,
        terms_updated=30,
        execution_time_seconds=Decimal("12.5"),
        started_at=now,
        completed_at=now,
        error_message=None,
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["job_id"] == "job-123"
    assert body["terms_processed"] == 100
    assert body["execution_time_seconds"] == 12.5
    datetime.fromisoformat(body["started_at"])
