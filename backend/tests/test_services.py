"""Tests for service layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.models.translations import Translation, TranslationDirection, TranslationRequest
from src.models.users import User, UserTier, UserStatus
from src.models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from src.services.translation_service import TranslationService
from src.services.user_service import UserService
from src.services.subscription_service import SubscriptionService
from src.utils.exceptions import BusinessLogicError, SystemError


class TestTranslationService:
    """Test TranslationService."""

    @pytest.fixture
    def translation_service(self, mock_bedrock_client, mock_config):
        """Create TranslationService with mocked dependencies."""
        with patch('src.services.translation_service.boto3.client') as mock_boto3:
            mock_boto3.return_value = mock_bedrock_client
            service = TranslationService()
            return service

    def test_translate_english_to_genz(self, translation_service, sample_user):
        """Test translation from English to GenZ."""
        request = TranslationRequest(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        result = translation_service.translate(request, sample_user)

        assert result.translation_id is not None
        assert result.user_id == sample_user.user_id
        assert result.original_text == "Hello world"
        assert result.translated_text == "Hola mundo"
        assert result.direction == TranslationDirection.ENGLISH_TO_GENZ
        assert result.confidence_score > 0

    def test_translate_genz_to_english(self, translation_service, sample_user):
        """Test translation from GenZ to English."""
        request = TranslationRequest(
            text="Hola mundo",
            direction=TranslationDirection.GENZ_TO_ENGLISH
        )

        result = translation_service.translate(request, sample_user)

        assert result.translation_id is not None
        assert result.user_id == sample_user.user_id
        assert result.original_text == "Hola mundo"
        assert result.translated_text == "Hello world"
        assert result.direction == TranslationDirection.GENZ_TO_ENGLISH

    def test_translate_with_empty_text(self, translation_service, sample_user):
        """Test translation with empty text raises error."""
        request = TranslationRequest(
            text="",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        with pytest.raises(BusinessLogicError):
            translation_service.translate(request, sample_user)

    def test_translate_with_long_text(self, translation_service, sample_user):
        """Test translation with text exceeding limit raises error."""
        long_text = "x" * 1001  # Exceeds 1000 character limit
        request = TranslationRequest(
            text=long_text,
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        with pytest.raises(BusinessLogicError):
            translation_service.translate(request, sample_user)

    def test_bedrock_api_error_handling(self, translation_service, sample_user, mock_bedrock_client):
        """Test handling of Bedrock API errors."""
        # Mock Bedrock client to raise an exception
        mock_bedrock_client.invoke_model.side_effect = Exception("API Error")

        request = TranslationRequest(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        with pytest.raises(SystemError):
            translation_service.translate(request, sample_user)

    def test_translation_history_storage_premium_user(self, translation_service, sample_premium_user):
        """Test that translations are stored for premium users."""
        request = TranslationRequest(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        with patch.object(translation_service, '_save_translation_history') as mock_save:
            translation_service.translate(request, sample_premium_user)
            mock_save.assert_called_once()

    def test_translation_history_not_stored_free_user(self, translation_service, sample_user):
        """Test that translations are not stored for free users."""
        request = TranslationRequest(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        )

        with patch.object(translation_service, '_save_translation_history') as mock_save:
            translation_service.translate(request, sample_user)
            mock_save.assert_not_called()


class TestUserService:
    """Test UserService."""

    @pytest.fixture
    def user_service(self, mock_dynamodb_table, mock_config):
        """Create UserService with mocked dependencies."""
        with patch('src.services.user_service.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            service = UserService()
            service.user_repository = mock_repo
            return service

    def test_get_user_profile(self, user_service, sample_user):
        """Test getting user profile."""
        user_service.user_repository.get_user.return_value = sample_user

        result = user_service.get_user_profile("test_user_123")

        assert result == sample_user
        user_service.user_repository.get_user.assert_called_once_with("test_user_123")

    def test_get_user_profile_not_found(self, user_service):
        """Test getting user profile when user doesn't exist."""
        user_service.user_repository.get_user.return_value = None

        result = user_service.get_user_profile("nonexistent_user")

        assert result is None

    def test_get_user_usage(self, user_service, sample_user):
        """Test getting user usage statistics."""
        user_service.user_repository.get_user.return_value = sample_user
        user_service.user_repository.get_usage_limits.return_value = {
            "daily_used": 5,
            "daily_limit": 10,
            "tier": "free"
        }

        result = user_service.get_user_usage("test_user_123")

        assert result["user_id"] == "test_user_123"
        assert result["daily_used"] == 5
        assert result["daily_limit"] == 10
        assert result["tier"] == "free"

    def test_upgrade_user_to_premium(self, user_service, sample_user):
        """Test upgrading user to premium."""
        user_service.user_repository.get_user.return_value = sample_user
        user_service.user_repository.update_user_tier.return_value = True

        result = user_service.upgrade_user_to_premium("test_user_123")

        assert result is True
        user_service.user_repository.update_user_tier.assert_called_once_with(
            "test_user_123", "premium"
        )

    def test_upgrade_nonexistent_user(self, user_service):
        """Test upgrading user that doesn't exist."""
        user_service.user_repository.get_user.return_value = None

        with pytest.raises(BusinessLogicError):
            user_service.upgrade_user_to_premium("nonexistent_user")

    def test_check_usage_limits_free_user(self, user_service, sample_user):
        """Test usage limit checking for free user."""
        user_service.user_repository.get_usage_limits.return_value = {
            "daily_used": 10,
            "daily_limit": 10,
            "tier": "free"
        }

        with pytest.raises(BusinessLogicError):
            user_service.check_usage_limits("test_user_123")

    def test_check_usage_limits_premium_user(self, user_service, sample_premium_user):
        """Test usage limit checking for premium user."""
        user_service.user_repository.get_usage_limits.return_value = {
            "daily_used": 100,
            "daily_limit": 1000,
            "tier": "premium"
        }

        # Should not raise exception for premium user
        user_service.check_usage_limits("premium_user_456")


class TestSubscriptionService:
    """Test SubscriptionService."""

    @pytest.fixture
    def subscription_service(self, mock_config):
        """Create SubscriptionService with mocked dependencies."""
        with patch('src.services.subscription_service.SubscriptionRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            service = SubscriptionService()
            service.subscription_repository = mock_repo
            return service

    def test_get_user_subscription(self, subscription_service, sample_subscription):
        """Test getting user subscription."""
        subscription_service.subscription_repository.get_active_subscription.return_value = sample_subscription

        result = subscription_service.get_user_subscription("premium_user_456")

        assert result == sample_subscription
        subscription_service.subscription_repository.get_active_subscription.assert_called_once_with("premium_user_456")

    def test_get_user_subscription_not_found(self, subscription_service):
        """Test getting user subscription when none exists."""
        subscription_service.subscription_repository.get_active_subscription.return_value = None

        result = subscription_service.get_user_subscription("free_user_123")

        assert result is None

    def test_create_subscription(self, subscription_service, sample_subscription):
        """Test creating a new subscription."""
        subscription_service.subscription_repository.create_subscription.return_value = sample_subscription

        result = subscription_service.create_subscription(
            user_id="premium_user_456",
            provider=SubscriptionProvider.APPLE,
            product_id="premium_monthly",
            transaction_id="txn_123"
        )

        assert result == sample_subscription
        subscription_service.subscription_repository.create_subscription.assert_called_once()

    def test_cancel_subscription(self, subscription_service):
        """Test canceling a subscription."""
        subscription_service.subscription_repository.cancel_subscription.return_value = True

        result = subscription_service.cancel_subscription("sub_123")

        assert result is True
        subscription_service.subscription_repository.cancel_subscription.assert_called_once_with("sub_123")

    def test_is_user_premium_with_active_subscription(self, subscription_service, sample_subscription):
        """Test premium status check with active subscription."""
        subscription_service.subscription_repository.get_active_subscription.return_value = sample_subscription

        result = subscription_service.is_user_premium("premium_user_456")

        assert result is True

    def test_is_user_premium_without_subscription(self, subscription_service):
        """Test premium status check without subscription."""
        subscription_service.subscription_repository.get_active_subscription.return_value = None

        result = subscription_service.is_user_premium("free_user_123")

        assert result is False

    def test_is_user_premium_with_expired_subscription(self, subscription_service):
        """Test premium status check with expired subscription."""
        expired_subscription = sample_subscription.copy()
        expired_subscription.status = SubscriptionStatus.EXPIRED
        subscription_service.subscription_repository.get_active_subscription.return_value = expired_subscription

        result = subscription_service.is_user_premium("expired_user_789")

        assert result is False
