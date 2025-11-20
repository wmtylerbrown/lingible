from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from models.config import UsageLimitsConfig, CognitoConfig
from models.translations import UsageLimit
from models.users import (
    User,
    UserTier,
    UserStatus,
    UserResponse,
    UserUsageResponse,
    UpgradeResponse,
    AccountDeletionResponse,
)
from services.user_service import UserService
from utils.exceptions import ValidationError
from utils.response import create_model_response


class DummyUsageConfig:
    def __init__(self) -> None:
        self.free_daily_translations = 5
        self.premium_daily_translations = 50
        self.free_max_text_length = 200
        self.premium_max_text_length = 500
        self.free_history_retention_days = 7
        self.premium_history_retention_days = 365


@pytest.fixture
def user_service() -> tuple[UserService, Mock]:
    service = UserService.__new__(UserService)
    service.config_service = Mock()
    service.config_service.get_config.side_effect = (
        lambda config_type: DummyUsageConfig()
        if config_type is UsageLimitsConfig
        else SimpleNamespace(user_pool_id="pool", user_pool_client_id="client", user_pool_region="us-east-1")  # CognitoConfig
    )
    repository = Mock()
    service.repository = repository
    service.user_repository = repository
    service.usage_config = DummyUsageConfig()
    return service, repository


def test_create_user_calls_repository(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    user = service.create_user("user-1", "tester", "test@example.com", UserTier.PREMIUM)
    repository.create_user.assert_called_once()
    assert user.tier is UserTier.PREMIUM


def test_get_user_delegates_to_repository(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = "user"
    assert service.get_user("user-1") == "user"
    repository.get_user.assert_called_once_with("user-1")


def test_get_user_usage_creates_defaults_when_missing(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_usage_limits.return_value = None
    repository.get_user.return_value = User(
        user_id="user-1",
        email="test@example.com",
        username="tester",
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
    )
    service._create_default_usage_limits = Mock(return_value=UsageLimit(tier=UserTier.FREE, daily_used=0, reset_daily_at=datetime.now(timezone.utc)))
    result = service.get_user_usage("user-1")
    service._create_default_usage_limits.assert_called_once()
    assert result.daily_limit == service.usage_config.free_daily_translations


def test_get_user_usage_resets_when_new_day(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    usage_limit = UsageLimit(
        tier=UserTier.FREE,
        daily_used=3,
        reset_daily_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    repository.get_usage_limits.return_value = usage_limit
    with patch("services.user_service.is_new_day_central_time", return_value=True), patch(
        "services.user_service.get_central_midnight_tomorrow",
        return_value=datetime(2025, 1, 2, tzinfo=timezone.utc),
    ):
        response = service.get_user_usage("user-1")
    repository.reset_daily_usage.assert_called_once()
    assert response.daily_used == 0


def test_upgrade_user_tier_updates_limits(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = User(
        user_id="user-1",
        email="test@example.com",
        username="tester",
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
    )
    usage_limit = UsageLimit(
        tier=UserTier.FREE,
        daily_used=0,
        reset_daily_at=datetime.now(timezone.utc),
    )
    repository.get_usage_limits.return_value = usage_limit
    repository.delete_daily_quiz_count.return_value = 1
    service.upgrade_user_tier("user-1", UserTier.PREMIUM)
    repository.update_user.assert_called_once()
    repository.update_usage_limits.assert_called_once()
    repository.delete_daily_quiz_count.assert_called_once_with("user-1")


def test_upgrade_user_tier_creates_limits_when_missing(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = User(
        user_id="user-1",
        email="test@example.com",
        username="tester",
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
    )
    repository.get_usage_limits.return_value = None
    service._create_default_usage_limits = Mock()
    service.upgrade_user_tier("user-1", UserTier.PREMIUM)
    service._create_default_usage_limits.assert_called_once()


def test_downgrade_user_tier_validates_user(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = None
    with pytest.raises(ValidationError):
        service.downgrade_user_tier("missing", UserTier.FREE)


def test_downgrade_user_tier_updates_limits(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = User(
        user_id="user-1",
        email="test@example.com",
        username="tester",
        tier=UserTier.PREMIUM,
        status=UserStatus.ACTIVE,
    )
    usage_limit = UsageLimit(
        tier=UserTier.PREMIUM,
        daily_used=1,
        reset_daily_at=datetime.now(timezone.utc),
    )
    repository.get_usage_limits.return_value = usage_limit
    service.downgrade_user_tier("user-1", UserTier.FREE)
    repository.update_usage_limits.assert_called_with("user-1", usage_limit)


def test_delete_user_handles_cognito_error(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service

    def fake_get_config(config_type):
        if config_type is UsageLimitsConfig:
            return DummyUsageConfig()
        if config_type is CognitoConfig:
            return SimpleNamespace(user_pool_id="pool", user_pool_client_id="client", user_pool_region="region")
        raise ValueError(config_type)

    service.config_service.get_config.side_effect = fake_get_config
    with patch("services.user_service.get_cognito_client") as cognito_client_cls:
        cognito_client = cognito_client_cls.return_value
        cognito_client.admin_delete_user.side_effect = RuntimeError("boom")
        service.delete_user("user-1")
    repository.delete_all_quiz_data.assert_called_once_with("user-1")
    repository.delete_user.assert_called_once_with("user-1")


def test_increment_slang_counters_log_on_success(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.increment_slang_submitted.return_value = True
    repository.increment_slang_approved.return_value = True
    service.increment_slang_submitted("user-1")
    service.increment_slang_approved("user-1")
    repository.increment_slang_submitted.assert_called_once()
    repository.increment_slang_approved.assert_called_once()


def test_create_default_usage_limits_updates_repository(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    with patch("services.user_service.get_central_midnight_tomorrow", return_value=datetime(2025, 1, 1, tzinfo=timezone.utc)):
        result = service._create_default_usage_limits("user-1", UserTier.FREE)
    repository.update_usage_limits.assert_called_once()
    assert result.daily_used == 0


def test_increment_and_reset_usage_delegate(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    service.increment_usage("user-1", UserTier.PREMIUM)
    service.reset_daily_usage("user-1", UserTier.PREMIUM)
    repository.increment_usage.assert_called_once_with("user-1", UserTier.PREMIUM)
    repository.reset_daily_usage.assert_called_once_with("user-1", UserTier.PREMIUM)


def test_suspend_user_sets_status(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = User(
        user_id="user-1",
        email="test@example.com",
        username="tester",
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
    )
    service.suspend_user("user-1")
    repository.update_user.assert_called_once()


def test_suspend_user_requires_existing(user_service: tuple[UserService, Mock]) -> None:
    service, repository = user_service
    repository.get_user.return_value = None
    with pytest.raises(ValidationError):
        service.suspend_user("user-1")


def test_user_profile_response_serialization_matches_api_contract() -> None:
    created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    user = User(
        user_id="user-123",
        email="test@example.com",
        username="tester",
        tier=UserTier.PREMIUM,
        status=UserStatus.ACTIVE,
        slang_submitted_count=Decimal("5"),
        slang_approved_count=Decimal("2"),
        created_at=created_at,
        updated_at=created_at,
    )

    envelope = create_model_response(user.to_api_response())
    body = json.loads(envelope["body"])

    assert body["user_id"] == "user-123"
    assert body["tier"] == UserTier.PREMIUM.value
    assert body["status"] == UserStatus.ACTIVE.value
    assert isinstance(body["slang_submitted_count"], int)
    assert isinstance(body["slang_approved_count"], int)
    datetime.fromisoformat(body["created_at"])


def test_user_usage_response_serialization_matches_api_contract() -> None:
    response = UserUsageResponse(
        tier=UserTier.FREE,
        daily_limit=10,
        daily_used=3,
        daily_remaining=7,
        reset_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        current_max_text_length=280,
        free_tier_max_length=200,
        premium_tier_max_length=500,
        free_daily_limit=5,
        premium_daily_limit=50,
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["tier"] == UserTier.FREE.value
    assert body["daily_limit"] == 10
    assert body["daily_remaining"] == 7
    datetime.fromisoformat(body["reset_date"])
    assert body["premium_tier_max_length"] == 500


def test_upgrade_response_serialization_matches_api_contract() -> None:
    response = UpgradeResponse(
        success=True,
        message="Upgraded!",
        tier=UserTier.PREMIUM.value,
        expires_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["success"] is True
    assert body["tier"] == UserTier.PREMIUM.value
    datetime.fromisoformat(body["expires_at"])


def test_account_deletion_response_serialization_matches_api_contract() -> None:
    response = AccountDeletionResponse(
        success=True,
        message="Deleted",
        deleted_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        cleanup_summary={"translations_deleted": 42},
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["success"] is True
    datetime.fromisoformat(body["deleted_at"])
    assert body["cleanup_summary"]["translations_deleted"] == 42
