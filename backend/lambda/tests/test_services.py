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
from src.utils.exceptions import BusinessLogicError, SystemError, UsageLimitExceededError


class TestTranslationService:
    """Test TranslationService."""

    @pytest.fixture
    def translation_service(self, mock_bedrock_client, mock_config):
        """Create TranslationService with mocked dependencies."""
        with patch('src.services.translation_service.aws_services') as mock_aws_services:
            with patch('src.services.translation_service.get_config_service') as mock_get_config:
                mock_aws_services.bedrock_runtime = mock_bedrock_client
                mock_get_config.return_value = mock_config
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

    def test_daily_limit_blocks_translation_when_no_quota(self, translation_service):
        """Test that translation is blocked when user has no remaining daily quota."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        # Mock usage response with no remaining quota
        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=10,
            daily_remaining=0,  # No quota left!
            reset_date=datetime.now(timezone.utc)
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            mock_user_service.get_user_usage.return_value = usage_response

            # Should raise UsageLimitExceededError
            with pytest.raises(UsageLimitExceededError) as exc_info:
                translation_service.translate_text(request, user_id)

            # Verify the exception details
            exception = exc_info.value
            assert "daily" in exception.message
            assert exception.status_code == 429  # Too Many Requests
            assert exception.error_code == "BIZ_001"

            # Should not call increment_usage
            mock_user_service.increment_usage.assert_not_called()

    def test_daily_limit_allows_translation_with_quota(self, translation_service, mock_bedrock_client):
        """Test that translation proceeds when user has remaining quota."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        # Mock usage response with available quota
        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=5,
            daily_remaining=5,  # Quota available
            reset_date=datetime.now(timezone.utc)
        )

        # Mock successful Bedrock response
        mock_bedrock_response = {
            "body": Mock()
        }
        mock_bedrock_response["body"].read.return_value = '{"content": [{"text": "Yo, wassup world!"}], "usage": {"input_tokens": 5, "output_tokens": 8}}'
        mock_bedrock_client.invoke_model.return_value = mock_bedrock_response

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'translation_repository') as mock_repo:
                mock_user_service.get_user_usage.return_value = usage_response
                mock_repo.generate_translation_id.return_value = "trans_123"
                mock_repo.create_translation.return_value = True

                # Should succeed
                result = translation_service.translate_text(request, user_id)

                assert result is not None
                assert result.translated_text == "Yo, wassup world!"

                # Should call increment_usage after successful translation
                mock_user_service.increment_usage.assert_called_once_with(user_id, UserTier.FREE)

    def test_usage_not_incremented_on_bedrock_failure(self, translation_service, mock_bedrock_client):
        """Test that usage is not incremented if Bedrock call fails."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        # Mock usage response with available quota
        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=3,
            daily_remaining=7,
            reset_date=datetime.now(timezone.utc)
        )

        # Mock Bedrock failure
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock API error")

        with patch.object(translation_service, 'user_service') as mock_user_service:
            mock_user_service.get_user_usage.return_value = usage_response

            # Should raise exception
            with pytest.raises(Exception):
                translation_service.translate_text(request, user_id)

            # Usage should NOT be incremented on failure
            mock_user_service.increment_usage.assert_not_called()


class TestUserService:
    """Test UserService."""

    @pytest.fixture
    def user_service(self, mock_config):
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
            "daily_used": 7,
            "daily_limit": 10,
            "tier": "free"
        }

        result = user_service.get_user_usage("test_user_123")

        assert result["user_id"] == "test_user_123"
        assert result["daily_used"] == 7
        assert result["daily_limit"] == 10
        assert result["tier"] == "free"

    def test_upgrade_user_tier_to_premium(self, user_service, sample_user):
        """Test upgrading user tier to premium."""
        user_service.repository.get_user.return_value = sample_user
        user_service.repository.update_user.return_value = True

        result = user_service.upgrade_user_tier("test_user_123", UserTier.PREMIUM)

        assert result is True
        # Verify the user tier was updated
        user_service.repository.update_user.assert_called_once()
        updated_user = user_service.repository.update_user.call_args[0][0]
        assert updated_user.tier == UserTier.PREMIUM

    def test_upgrade_user_tier_nonexistent_user(self, user_service):
        """Test upgrading tier for user that doesn't exist."""
        user_service.repository.get_user.return_value = None

        with pytest.raises(ValidationError):
            user_service.upgrade_user_tier("nonexistent_user", UserTier.PREMIUM)

    def test_subscription_service_upgrade_flow(self):
        """Test that SubscriptionService properly calls UserService.upgrade_user_tier."""
        from src.services.subscription_service import SubscriptionService
        from src.models.users import UserTier
        from unittest.mock import Mock, patch

        # Create mocks
        mock_user = Mock()
        mock_user.user_id = "test_user_123"
        mock_user.tier = UserTier.FREE

        with patch('src.services.subscription_service.UserService') as MockUserService:
            with patch('src.services.subscription_service.SubscriptionRepository') as MockSubRepo:
                with patch('src.services.subscription_service.ReceiptValidationService') as MockReceiptService:

                    # Setup mocks
                    mock_user_service = MockUserService.return_value
                    mock_user_service.get_user.return_value = mock_user
                    mock_user_service.upgrade_user_tier.return_value = True

                    mock_sub_repo = MockSubRepo.return_value
                    mock_sub_repo.create_subscription.return_value = True

                    mock_receipt_service = MockReceiptService.return_value
                    mock_validation_result = Mock()
                    mock_validation_result.is_valid = True
                    mock_receipt_service.validate_receipt.return_value = mock_validation_result

                    # Test the subscription upgrade flow
                    subscription_service = SubscriptionService()

                    result_user = subscription_service.upgrade_user(
                        "test_user_123", "apple", "receipt_data", "transaction_123"
                    )

                    # Verify the correct UserService method was called
                    mock_user_service.upgrade_user_tier.assert_called_once()

                    # Verify the call arguments
                    call_args = mock_user_service.upgrade_user_tier.call_args
                    assert call_args[0][0] == "test_user_123"  # user_id
                    assert call_args[0][1].value == "premium"  # tier value

                    # Verify subscription was created
                    mock_sub_repo.create_subscription.assert_called_once()

                    # Verify user was fetched twice (initial + after tier update)
                    assert mock_user_service.get_user.call_count == 2

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
            "daily_used": 95,
            "daily_limit": 100,
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

    def test_is_user_premium_with_expired_subscription(self, subscription_service, sample_subscription):
        """Test premium status check with expired subscription."""
        expired_subscription = sample_subscription.copy()
        expired_subscription.status = SubscriptionStatus.EXPIRED
        subscription_service.subscription_repository.get_active_subscription.return_value = expired_subscription

        result = subscription_service.is_user_premium("expired_user_789")

        assert result is False
