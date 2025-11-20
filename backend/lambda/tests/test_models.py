"""Tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError

from src.models.users import User, UserTier, UserStatus
from src.models.translations import Translation, TranslationDirection, TranslationRequest
from src.models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from src.models.events import (
    TranslationEvent,
    SimpleAuthenticatedEvent,
    PathParameterEvent
)


class TestUserModel:
    """Test User model."""

    def test_valid_user_creation(self):
        """Test creating a valid user."""
        user = User(
            user_id="test_user_123",
            email="test@example.com",
            username="testuser",
            tier=UserTier.FREE,
            status=UserStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        assert user.user_id == "test_user_123"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.tier == "free"
        assert user.status == "active"

    def test_user_with_premium_tier(self):
        """Test creating a user with premium tier."""
        user = User(
            user_id="test_user_123",
            email="test@example.com",
            username="testuser",
            tier=UserTier.PREMIUM,
            status=UserStatus.ACTIVE,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        assert user.tier == "premium"
        assert user.status == "active"

    def test_invalid_user_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            User(
                email="test@example.com",
                username="testuser"
                # Missing user_id, tier, status, etc.
            )

    def test_invalid_email_format(self):
        """Test that invalid email format raises ValidationError."""
        with pytest.raises(ValidationError):
            User(
                user_id="test_user_123",
                email=None,  # None email should fail
                username="testuser",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z"
            )


class TestTranslationModel:
    """Test Translation model."""

    def test_valid_translation_creation(self):
        """Test creating a valid translation."""
        translation = Translation(
            translation_id="trans_789",
            original_text="Hello world",
            translated_text="Hola mundo",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            model_used="anthropic.claude-3-sonnet-20240229-v1:0",
            confidence_score=0.95,
            created_at="2024-01-01T00:00:00Z",
            daily_used=1,
            daily_limit=10,
            tier=UserTier.FREE,
        )

        assert translation.translation_id == "trans_789"
        assert translation.original_text == "Hello world"
        assert translation.translated_text == "Hola mundo"
        assert translation.direction == "english_to_genz"
        assert translation.confidence_score == Decimal("0.95")

    def test_translation_with_optional_fields(self):
        """Test creating a translation with optional fields."""
        translation = Translation(
            translation_id="trans_789",
            original_text="Hello world",
            translated_text="Hola mundo",
            direction=TranslationDirection.GENZ_TO_ENGLISH,
            model_used="anthropic.claude-3-sonnet-20240229-v1:0",
            confidence_score=0.95,
            created_at="2024-01-01T00:00:00Z",
            processing_time_ms=150,
            daily_used=5,
            daily_limit=20,
            tier=UserTier.PREMIUM,
        )

        assert translation.processing_time_ms == 150

    def test_invalid_confidence_score(self):
        """Test that confidence score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Translation(
                translation_id="trans_789",
                original_text="Hello world",
                translated_text="Hola mundo",
                direction=TranslationDirection.ENGLISH_TO_GENZ,
                model_used="anthropic.claude-3-sonnet-20240229-v1:0",
                confidence_score=1.5,  # Invalid: > 1
                created_at="2024-01-01T00:00:00Z",
                daily_used=0,
                daily_limit=5,
                tier=UserTier.FREE,
            )


class TestSubscriptionModel:
    """Test Subscription model."""

    def test_valid_subscription_creation(self):
        """Test creating a valid subscription."""
        subscription = UserSubscription(
            user_id="premium_user_456",
            provider=SubscriptionProvider.APPLE,
            transaction_id="txn_123",
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

        assert subscription.user_id == "premium_user_456"
        assert subscription.provider == "apple"
        assert subscription.transaction_id == "txn_123"
        assert subscription.status == "active"

    def test_subscription_with_optional_fields(self):
        """Test creating a subscription with optional fields."""
        subscription = UserSubscription(
            user_id="premium_user_456",
            provider=SubscriptionProvider.GOOGLE,
            transaction_id="txn_789",
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

        assert subscription.transaction_id == "txn_789"


class TestEventModels:
    """Test event models."""

    def test_translation_event(self):
        """Test TranslationEvent."""
        event = TranslationEvent(
            event={},
            request_body=TranslationRequest(
                text="Hello world",
                direction=TranslationDirection.ENGLISH_TO_GENZ
            ),
            user_id="test_user_123",
            request_id="req_123",
            timestamp="2024-01-01T00:00:00Z"
        )

        assert event.user_id == "test_user_123"
        assert event.request_id == "req_123"
        assert event.request_body.text == "Hello world"
        assert event.request_body.direction == "english_to_genz"

    def test_simple_authenticated_event(self):
        """Test SimpleAuthenticatedEvent."""
        event = SimpleAuthenticatedEvent(
            event={},
            user_id="test_user_123",
            request_id="req_123"
        )

        assert event.user_id == "test_user_123"

    def test_path_parameter_event(self):
        """Test PathParameterEvent."""
        event = PathParameterEvent(
            event={},
            user_id="test_user_123",
            request_id="req_123",
            path_parameters={"id": "trans_789"}
        )

        assert event.path_parameters["id"] == "trans_789"


class TestEnums:
    """Test enum values."""

    def test_user_tier_enum(self):
        """Test UserTier enum values."""
        assert UserTier.FREE.value == "free"
        assert UserTier.PREMIUM.value == "premium"

    def test_user_status_enum(self):
        """Test UserStatus enum values."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.CANCELLED.value == "cancelled"

    def test_translation_direction_enum(self):
        """Test TranslationDirection enum values."""
        assert TranslationDirection.ENGLISH_TO_GENZ.value == "english_to_genz"
        assert TranslationDirection.GENZ_TO_ENGLISH.value == "genz_to_english"

    def test_subscription_status_enum(self):
        """Test SubscriptionStatus enum values."""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.CANCELLED.value == "cancelled"
        assert SubscriptionStatus.EXPIRED.value == "expired"

    def test_subscription_provider_enum(self):
        """Test SubscriptionProvider enum values."""
        assert SubscriptionProvider.APPLE.value == "apple"
        assert SubscriptionProvider.GOOGLE.value == "google"
