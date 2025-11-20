from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from models.config import UsageLimitsConfig
from models.translations import (
    Translation,
    TranslationDirection,
    TranslationHistory,
    TranslationHistoryServiceResult,
    TranslationRequestInternal,
)
from models.users import UserTier, UserUsageResponse
from repositories.translation_repository import QueryResult
from services.translation_service import TranslationService
from utils.exceptions import (
    InsufficientPermissionsError,
    UsageLimitExceededError,
    ValidationError,
)
from utils.response import create_model_response


class DummyConfigService:
    def __init__(self) -> None:
        self._usage = UsageLimitsConfig(
            free_daily_translations=5,
            premium_daily_translations=50,
            free_max_text_length=200,
            premium_max_text_length=500,
            free_history_retention_days=7,
            premium_history_retention_days=365,
        )

    def get_config(self, config_type):
        if config_type is UsageLimitsConfig:
            return self._usage
        raise ValueError(config_type)


def _make_usage_response(
    *,
    tier: UserTier = UserTier.PREMIUM,
    daily_limit: int = 10,
    daily_used: int = 2,
    daily_remaining: int = 8,
    current_max_text_length: int = 280,
) -> UserUsageResponse:
    return UserUsageResponse(
        tier=tier,
        daily_limit=daily_limit,
        daily_used=daily_used,
        daily_remaining=daily_remaining,
        reset_date=datetime.now(timezone.utc),
        current_max_text_length=current_max_text_length,
        free_tier_max_length=200,
        premium_tier_max_length=500,
        free_daily_limit=5,
        premium_daily_limit=50,
    )


@pytest.fixture
def usage_response() -> UserUsageResponse:
    return UserUsageResponse(
        tier=UserTier.PREMIUM,
        daily_limit=10,
        daily_used=2,
        daily_remaining=8,
        reset_date=datetime.now(timezone.utc),
        current_max_text_length=280,
        free_tier_max_length=200,
        premium_tier_max_length=500,
        free_daily_limit=5,
        premium_daily_limit=50,
    )


@pytest.fixture
def translation_service_with_mocks() -> tuple[TranslationService, Mock, Mock, Mock]:
    config = DummyConfigService()
    service = TranslationService.__new__(TranslationService)
    service.config_service = config
    service.translation_repository = Mock()
    service.user_service = Mock()
    service.usage_config = config.get_config(UsageLimitsConfig)
    service.slang_service = Mock()
    service.slang_service.config = SimpleNamespace(
        low_confidence_threshold=Decimal("0.50"),
        model="mock-model",
    )
    return service, service.translation_repository, service.user_service, service.slang_service


def _build_request(text: str = "hello", direction: TranslationDirection = TranslationDirection.ENGLISH_TO_GENZ) -> TranslationRequestInternal:
    return TranslationRequestInternal(text=text, direction=direction, user_id="user-123")


def test_translate_text_success_saves_history_and_increments_usage(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock],
) -> None:
    service, repo, user_service, slang_service = translation_service_with_mocks
    usage_response = _make_usage_response()

    repo.generate_translation_id.return_value = "trans-123"
    repo.create_translation.return_value = True

    user_service.get_user_usage.return_value = usage_response
    user_service.get_user.return_value = Mock(tier="premium")

    slang_service.translate_to_genz.return_value = Mock(
        translated="sup", confidence=Decimal("0.95")
    )

    response = service.translate_text(_build_request(), "user-123")

    assert response.translation_id == "trans-123"
    assert response.translated_text == "sup"
    assert response.translation_failed is False
    assert response.daily_used == usage_response.daily_used + 1

    user_service.increment_usage.assert_called_once_with("user-123", usage_response.tier)
    repo.create_translation.assert_called_once()


def test_translate_text_same_text_skips_usage_and_history(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock],
) -> None:
    service, repo, user_service, slang_service = translation_service_with_mocks
    usage_response = _make_usage_response(tier=UserTier.FREE)

    repo.generate_translation_id.return_value = "trans-456"
    user_service.get_user_usage.return_value = usage_response
    user_service.get_user.return_value = Mock(tier="free")
    slang_service.translate_to_genz.return_value = Mock(
        translated="hello", confidence=Decimal("0.20")
    )

    response = service.translate_text(_build_request(text="hello"), "user-123")

    assert response.translation_failed is True
    assert response.user_message is not None
    user_service.increment_usage.assert_not_called()
    repo.create_translation.assert_not_called()


def test_translate_text_raises_usage_limit_exceeded(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, _repo, user_service, slang_service = translation_service_with_mocks
    usage_response = _make_usage_response(daily_remaining=0)

    user_service.get_user_usage.return_value = usage_response
    slang_service.translate_to_genz.return_value = Mock(
        translated="sup", confidence=Decimal("0.9")
    )

    with pytest.raises(UsageLimitExceededError):
        service.translate_text(_build_request(), "user-123")


def test_translate_text_validates_text_length(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, _repo, user_service, _slang_service = translation_service_with_mocks
    usage_response = _make_usage_response()
    user_service.get_user_usage.return_value = usage_response

    over_limit_text = "x" * (usage_response.current_max_text_length + 1)
    with pytest.raises(ValidationError):
        service.translate_text(_build_request(text=over_limit_text), "user-123")


def test_save_translation_history_only_for_premium() -> None:
    response = Translation(
        original_text="hello",
        translated_text="sup",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        confidence_score=Decimal("0.9"),
        translation_id="trans-999",
        created_at=datetime.now(timezone.utc),
        processing_time_ms=123,
        model_used="mock-model",
        translation_failed=False,
        failure_reason=None,
        user_message=None,
        can_submit_feedback=False,
        daily_used=3,
        daily_limit=10,
        tier=UserTier.PREMIUM,
    )

    service = TranslationService.__new__(TranslationService)
    service.translation_repository = Mock()
    service.user_service = Mock()
    service.user_service.get_user.side_effect = [Mock(tier="premium"), Mock(tier="free")]

    # Premium user: history saved
    service._save_translation_history(response, "premium-user")
    service.translation_repository.create_translation.assert_called_once()

    # Free user: history skipped
    service.translation_repository.create_translation.reset_mock()
    service._save_translation_history(response, "free-user")
    service.translation_repository.create_translation.assert_not_called()


def test_is_same_text_handles_punctuation() -> None:
    service = TranslationService.__new__(TranslationService)
    assert service._is_same_text("Hello!", "hello ") is True
    assert service._is_same_text("different", "word") is False


def test_translate_text_invalid_direction(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, _repo, user_service, _slang_service = translation_service_with_mocks
    usage_response = _make_usage_response()
    user_service.get_user_usage.return_value = usage_response

    request = _build_request()
    object.__setattr__(request, "direction", "invalid")  # type: ignore[attr-defined]

    with pytest.raises(ValidationError):
        service.translate_text(request, "user-123")


def test_translate_text_handles_genz_to_english(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, slang_service = translation_service_with_mocks
    usage_response = _make_usage_response()

    repo.generate_translation_id.return_value = "trans-789"
    user_service.get_user_usage.return_value = usage_response
    user_service.get_user.return_value = Mock(tier="premium")
    slang_service.translate_to_english.return_value = Mock(
        translated="hello", confidence=Decimal("0.95")
    )

    response = service.translate_text(
        _build_request(direction=TranslationDirection.GENZ_TO_ENGLISH),
        "user-123",
    )

    assert response.translated_text == "hello"
    slang_service.translate_to_english.assert_called_once()


def test_validate_translation_request_empty_text() -> None:
    service = TranslationService.__new__(TranslationService)
    request = _build_request(text="temp")
    object.__setattr__(request, "text", "")
    with pytest.raises(ValidationError):
        service._validate_translation_request(request, max_text_length=100)


def test_is_premium_user_handles_exception() -> None:
    service = TranslationService.__new__(TranslationService)
    service.user_service = Mock()
    service.user_service.get_user.side_effect = RuntimeError("boom")
    assert service._is_premium_user("user-123") is False


def test_get_translation_history_requires_premium(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="free")

    with pytest.raises(InsufficientPermissionsError):
        service.get_translation_history("user-123")


def test_get_translation_history_returns_result(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="premium")
    history_item = TranslationHistory(
        translation_id="t1",
        user_id="user-123",
        original_text="hello",
        translated_text="sup",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        confidence_score=Decimal("0.8"),
        created_at=datetime.now(timezone.utc),
        model_used="mock-model",
    )
    repo.get_user_translations.return_value = QueryResult(
        items=[history_item],
        count=1,
        last_evaluated_key=None,
        scanned_count=1,
    )

    result = service.get_translation_history("user-123")
    assert result.total_count == 1
    repo.get_user_translations.assert_called_once()


def test_delete_translation_requires_premium(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="free")

    with pytest.raises(InsufficientPermissionsError):
        service.delete_translation("user-123", "trans-1")


def test_delete_translation_logs_when_not_found(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="premium")
    repo.delete_translation.return_value = False

    assert service.delete_translation("user-123", "trans-1") is False


def test_delete_user_translations_requires_premium(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="free")

    with pytest.raises(InsufficientPermissionsError):
        service.delete_user_translations("user-123")


def test_delete_user_translations_allows_account_deletion(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, _ = translation_service_with_mocks
    user_service.get_user.return_value = Mock(tier="free")
    repo.get_user_translations.return_value = QueryResult(
        items=[
            SimpleNamespace(translation_id="t1"),
            SimpleNamespace(translation_id="t2"),
        ],
        count=2,
        last_evaluated_key=None,
        scanned_count=2,
    )
    repo.delete_translation.return_value = True

    deleted = service.delete_user_translations("user-123", is_account_deletion=True)
    assert deleted == 2


def test_translate_text_response_serialization_matches_api_contract(
    translation_service_with_mocks: tuple[TranslationService, Mock, Mock, Mock]
) -> None:
    service, repo, user_service, slang_service = translation_service_with_mocks
    usage_response = _make_usage_response()

    repo.generate_translation_id.return_value = "trans-contract"
    repo.create_translation.return_value = True
    user_service.get_user_usage.return_value = usage_response
    user_service.get_user.return_value = Mock(tier="premium")
    slang_service.translate_to_genz.return_value = Mock(
        translated="sup fam", confidence=Decimal("0.87")
    )

    translation = service.translate_text(_build_request(), "user-123")
    response = create_model_response(translation)
    body = json.loads(response["body"])

    assert body["translation_id"] == "trans-contract"
    assert body["direction"] == TranslationDirection.ENGLISH_TO_GENZ.value
    assert body["translated_text"] == "sup fam"
    assert isinstance(body["confidence_score"], float)
    # ensure datetime serialized to ISO 8601
    datetime.fromisoformat(body["created_at"])
    assert isinstance(body["daily_used"], int)
    assert isinstance(body["translation_failed"], bool)
    assert body["tier"] == usage_response.tier.value


def test_translation_history_response_serialization_matches_api_contract() -> None:
    created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history = TranslationHistory(
        translation_id="t-history",
        user_id="user-55",
        original_text="hello",
        translated_text="yo",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        confidence_score=Decimal("0.77"),
        created_at=created_at,
        model_used="mock-model",
    )
    result = TranslationHistoryServiceResult(
        translations=[history],
        total_count=1,
        has_more=False,
        last_evaluated_key=None,
    )

    api_response = create_model_response(result)
    body = json.loads(api_response["body"])

    assert body["total_count"] == 1
    assert body["has_more"] is False
    assert body["last_evaluated_key"] is None
    assert isinstance(body["translations"], list) and len(body["translations"]) == 1
    first = body["translations"][0]
    assert first["translation_id"] == "t-history"
    assert first["direction"] == TranslationDirection.ENGLISH_TO_GENZ.value
    assert isinstance(first["confidence_score"], float)
    datetime.fromisoformat(first["created_at"])
