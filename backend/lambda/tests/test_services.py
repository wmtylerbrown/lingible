"""Tests for service layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from models.translations import Translation, TranslationDirection, TranslationRequest
from models.users import User, UserTier, UserStatus
from models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from models.trending import TrendingTerm, TrendingCategory, TrendingJobRequest
from services.translation_service import TranslationService
from services.user_service import UserService
from services.subscription_service import SubscriptionService
from services.trending_service import TrendingService
from utils.exceptions import BusinessLogicError, SystemError, UsageLimitExceededError, ValidationError


class TestTranslationService:
    """Test TranslationService."""

    @pytest.fixture
    def translation_service(self, mock_config):
        """Create TranslationService with mocked dependencies."""
        with patch('services.translation_service.get_config_service') as mock_get_config:
            with patch('services.translation_service.TranslationRepository') as mock_repo_class:
                with patch('services.translation_service.UserService') as mock_user_service_class:
                    with patch('services.translation_service.SlangService') as mock_slang_service_class:
                        mock_get_config.return_value = mock_config

                        # Create mock instances
                        mock_repo_class.return_value = Mock()
                        mock_user_service_class.return_value = Mock()

                        # Configure slang service mock with config
                        mock_slang_service = Mock()
                        mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                        mock_slang_service.config.low_confidence_threshold = 0.3
                        mock_slang_service_class.return_value = mock_slang_service

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
        long_text = "x" * 101  # Exceeds 100 character limit for premium
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
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
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

    def test_translation_fails_when_returning_same_text(self, translation_service):
        """Test that translation is marked as failed when it returns the same text."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        # Mock usage response
        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=5,
            daily_remaining=5,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Mock slang service to return same text (translation failed)
        slang_result = SlangTranslationResponse(
            translated="Hello world",  # Same as input!
            confidence=Decimal("0.2"),
            applied_terms=[]
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_slang_service.translate_to_genz.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.3
                    mock_repo.generate_translation_id.return_value = "trans_123"

                    result = translation_service.translate_text(request, user_id)

                    # Translation should be marked as failed
                    from utils.translation_messages import TranslationMessages
                    assert result.translation_failed is True
                    assert result.failure_reason == "low_confidence"
                    assert result.user_message is not None
                    assert result.user_message in TranslationMessages.LOW_CONFIDENCE

                    # Usage should NOT be incremented
                    mock_user_service.increment_usage.assert_not_called()

                    # Daily used should remain the same
                    assert result.daily_used == usage_response.daily_used

                    # Translation history should NOT be saved
                    mock_repo.create_translation.assert_not_called()

                    # can_submit_feedback should be False for free users
                    assert result.can_submit_feedback is False

    def test_translation_fails_with_no_translation_needed_message(self, translation_service):
        """Test translation failure with 'no translation needed' message for higher confidence."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="This is already plain English",
            direction=TranslationDirection.GENZ_TO_ENGLISH,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=3,
            daily_remaining=7,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Mock slang service - same text but higher confidence
        slang_result = SlangTranslationResponse(
            translated="This is already plain English",  # Same text
            confidence=Decimal("0.8"),  # Higher confidence
            applied_terms=[]
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_slang_service.translate_to_english.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.3
                    mock_repo.generate_translation_id.return_value = "trans_456"

                    result = translation_service.translate_text(request, user_id)

                    # Should be marked as failed
                    from utils.translation_messages import TranslationMessages
                    assert result.translation_failed is True
                    assert result.failure_reason == "no_translation_needed"
                    assert result.user_message is not None
                    assert result.user_message in TranslationMessages.NO_TRANSLATION_GENZ_TO_ENGLISH

                    # Usage should NOT be incremented
                    mock_user_service.increment_usage.assert_not_called()

    def test_premium_user_can_submit_feedback_on_failure(self, translation_service):
        """Test that premium users get can_submit_feedback=True on translation failure."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse, User, UserStatus
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "premium_user_456"
        request = TranslationRequestInternal(
            text="obscure slang",
            direction=TranslationDirection.GENZ_TO_ENGLISH,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.PREMIUM,
            daily_limit=100,
            daily_used=5,
            daily_remaining=95,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=500,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Mock slang service - translation failed
        slang_result = SlangTranslationResponse(
            translated="obscure slang",  # Same text
            confidence=Decimal("0.4"),
            applied_terms=[]
        )

        # Mock premium user
        mock_premium_user = User(
            user_id=user_id,
            email="premium@test.com",
            username="premiumuser",
            tier=UserTier.PREMIUM,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_user_service.get_user.return_value = mock_premium_user
                    mock_slang_service.translate_to_english.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.3
                    mock_repo.generate_translation_id.return_value = "trans_premium"

                    result = translation_service.translate_text(request, user_id)

                    # Premium user should be able to submit feedback
                    from utils.translation_messages import TranslationMessages
                    assert result.translation_failed is True
                    assert result.can_submit_feedback is True  # Premium user!
                    assert result.user_message in TranslationMessages.NO_TRANSLATION_GENZ_TO_ENGLISH

    def test_translation_succeeds_and_charges_when_text_differs(self, translation_service):
        """Test that successful translation charges usage and saves history."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.PREMIUM,
            daily_limit=100,
            daily_used=10,
            daily_remaining=90,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=500,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Mock successful translation - different text
        slang_result = SlangTranslationResponse(
            translated="Yo what's good world",  # Different text!
            confidence=Decimal("0.95"),
            applied_terms=["hello -> yo what's good"]
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    # Mock user service for both usage and premium check
                    from models.users import User, UserStatus
                    mock_user = User(
                        user_id=user_id,
                        email="premium@test.com",
                        username="premiumuser",
                        tier=UserTier.PREMIUM,
                        status=UserStatus.ACTIVE,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_user_service.get_user.return_value = mock_user  # For premium check

                    mock_slang_service.translate_to_genz.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_repo.generate_translation_id.return_value = "trans_789"
                    mock_repo.create_translation.return_value = True

                    result = translation_service.translate_text(request, user_id)

                    # Translation should succeed
                    assert result.translation_failed is False
                    assert result.failure_reason is None
                    assert result.user_message is None
                    assert result.can_submit_feedback is False  # Not a failure, so no feedback option

                    # Usage SHOULD be incremented
                    mock_user_service.increment_usage.assert_called_once_with(user_id, UserTier.PREMIUM)

                    # Daily used should be incremented
                    assert result.daily_used == usage_response.daily_used + 1

                    # Translation history SHOULD be saved (premium user)
                    mock_repo.create_translation.assert_called_once()

    def test_translation_failure_punctuation_differences_ignored(self, translation_service):
        """Test that punctuation-only differences are treated as failed translation."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Hello, world!",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=2,
            daily_remaining=8,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Mock translation with only punctuation differences
        slang_result = SlangTranslationResponse(
            translated="Hello world",  # Same but without punctuation
            confidence=Decimal("0.5"),
            applied_terms=[]
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_slang_service.translate_to_genz.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.3
                    mock_repo.generate_translation_id.return_value = "trans_punc"

                    result = translation_service.translate_text(request, user_id)

                    # Should be treated as failed (punctuation differences ignored)
                    assert result.translation_failed is True

                    # User should NOT be charged
                    mock_user_service.increment_usage.assert_not_called()
                    assert result.daily_used == usage_response.daily_used

    def test_message_randomization_works(self, translation_service):
        """Test that message randomization provides variety."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal
        from utils.translation_messages import TranslationMessages

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Test text",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=1,
            daily_remaining=9,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        slang_result = SlangTranslationResponse(
            translated="Test text",  # Same text
            confidence=Decimal("0.1"),  # Low confidence
            applied_terms=[]
        )

        messages_seen = set()

        # Run translation multiple times to test randomization
        for _ in range(20):
            with patch.object(translation_service, 'user_service') as mock_user_service:
                with patch.object(translation_service, 'slang_service') as mock_slang_service:
                    with patch.object(translation_service, 'translation_repository') as mock_repo:
                        mock_user_service.get_user_usage.return_value = usage_response
                        mock_slang_service.translate_to_genz.return_value = slang_result
                        mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                        mock_slang_service.config.low_confidence_threshold = 0.3
                        mock_repo.generate_translation_id.return_value = "trans_rand"

                        result = translation_service.translate_text(request, user_id)
                        messages_seen.add(result.user_message)

        # Should see variety (at least 2 different messages out of 5 possible)
        assert len(messages_seen) >= 2
        # All messages should be from the correct list
        for msg in messages_seen:
            assert msg in TranslationMessages.LOW_CONFIDENCE

    def test_configurable_confidence_threshold(self, translation_service):
        """Test that confidence threshold can be configured."""
        from src.models.translations import TranslationRequestInternal, TranslationDirection
        from src.models.users import UserUsageResponse
        from src.models.slang import SlangTranslationResponse
        from decimal import Decimal

        user_id = "test_user_123"
        request = TranslationRequestInternal(
            text="Test",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=user_id
        )

        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=1,
            daily_remaining=9,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=100,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100
        )

        # Test with confidence=0.25 (just below default threshold of 0.3)
        slang_result = SlangTranslationResponse(
            translated="Test",
            confidence=Decimal("0.25"),
            applied_terms=[]
        )

        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_slang_service.translate_to_genz.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.3
                    mock_repo.generate_translation_id.return_value = "trans_thresh"

                    result = translation_service.translate_text(request, user_id)

                    # Should be low_confidence because 0.25 < 0.3
                    assert result.failure_reason == "low_confidence"

        # Test with higher threshold (0.5)
        with patch.object(translation_service, 'user_service') as mock_user_service:
            with patch.object(translation_service, 'slang_service') as mock_slang_service:
                with patch.object(translation_service, 'translation_repository') as mock_repo:
                    mock_user_service.get_user_usage.return_value = usage_response
                    mock_slang_service.translate_to_genz.return_value = slang_result
                    mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                    mock_slang_service.config.low_confidence_threshold = 0.5  # Higher threshold!
                    mock_repo.generate_translation_id.return_value = "trans_thresh2"

                    result = translation_service.translate_text(request, user_id)

                    # Should still be low_confidence because 0.25 < 0.5
                    assert result.failure_reason == "low_confidence"


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
                with patch('src.services.subscription_service.AppleStoreKitService') as MockAppleService:

                    # Setup mocks
                    mock_user_service = MockUserService.return_value
                    mock_user_service.get_user.return_value = mock_user
                    mock_user_service.upgrade_user_tier.return_value = True

                    mock_sub_repo = MockSubRepo.return_value
                    mock_sub_repo.create_subscription.return_value = True

                    mock_apple_service = MockAppleService.return_value
                    mock_validation_result = Mock()
                    mock_validation_result.is_valid = True
                    mock_apple_service.validate_transaction.return_value = mock_validation_result

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


class TestTrendingService:
    """Test TrendingService with comprehensive unit tests."""

    @pytest.fixture
    def trending_service(self, mock_bedrock_client, mock_config):
        """Create TrendingService with mocked dependencies."""
        with patch('src.services.trending_service.aws_services') as mock_aws_services:
            with patch('src.services.trending_service.get_config_service') as mock_get_config:
                with patch('src.services.trending_service.UserService') as mock_user_service_class:
                    mock_aws_services.bedrock_client = mock_bedrock_client

                    # Mock the BedrockConfig specifically
                    from models.config import BedrockModel
                    mock_bedrock_config = BedrockModel(
                        model="anthropic.claude-3-sonnet-20240229-v1:0",
                        region="us-east-1",
                        max_tokens=1000,
                        temperature=0.7
                    )

                    # Set up the mock config to return the BedrockConfig when called
                    def mock_get_config_method(config_type, table_name=None):
                        if config_type == BedrockModel:
                            return mock_bedrock_config
                        return mock_config.get_config(config_type, table_name)

                    mock_config.get_config.side_effect = mock_get_config_method
                    mock_get_config.return_value = mock_config

                    # Mock UserService
                    mock_user_service = Mock()
                    mock_user_service_class.return_value = mock_user_service

                    service = TrendingService()
                    service.user_service = mock_user_service
                    return service

    def test_get_trending_terms_success(self, trending_service, sample_trending_term):
        """Test getting trending terms successfully."""
        # Mock repository response
        trending_service.repository.get_trending_terms.return_value = [sample_trending_term]
        trending_service.repository.get_trending_stats.return_value = {
            "total_active_terms": 1,
            "last_updated": "2024-01-15T10:00:00Z"
        }

        # Mock user service to return premium user
        from models.users import User, UserTier
        mock_user = User(
            user_id="premium_user_123",
            email="premium@example.com",
            username="premium_user",
            tier=UserTier.PREMIUM,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        trending_service.user_service.get_user.return_value = mock_user

        result = trending_service.get_trending_terms(user_id="premium_user_123", limit=10)

        assert result.total_count == 1
        assert len(result.terms) == 1
        assert result.terms[0].term == sample_trending_term.term
        assert result.terms[0].search_count == sample_trending_term.search_count  # Premium gets full data

    def test_get_trending_terms_free_tier_limits(self, trending_service, sample_trending_term):
        """Test free tier limitations on trending terms."""
        # Mock repository response
        trending_service.repository.get_trending_terms.return_value = [sample_trending_term]
        trending_service.repository.get_trending_stats.return_value = {
            "total_active_terms": 1,
            "last_updated": "2024-01-15T10:00:00Z"
        }

        # Mock user service to return free user
        from models.users import User, UserTier
        mock_user = User(
            user_id="free_user_123",
            email="free@example.com",
            username="free_user",
            tier=UserTier.FREE,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        trending_service.user_service.get_user.return_value = mock_user

        # Test limit enforcement
        result = trending_service.get_trending_terms(user_id="free_user_123", limit=50)

        # Should be limited to 10 terms max
        trending_service.repository.get_trending_terms.assert_called_with(limit=10, category=None, active_only=True)

        # Free tier should get limited data
        assert result.terms[0].search_count == 0  # Hidden for free users
        assert result.terms[0].example_usage is None  # Hidden for free users

    def test_get_trending_terms_free_tier_category_restriction(self, trending_service):
        """Test free tier category restrictions."""
        # Mock user service to return free user
        from models.users import User, UserTier
        mock_user = User(
            user_id="free_user_123",
            email="free@example.com",
            username="free_user",
            tier=UserTier.FREE,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        trending_service.user_service.get_user.return_value = mock_user

        with pytest.raises(ValidationError, match="Category filtering is a premium feature"):
            trending_service.get_trending_terms(user_id="free_user_123", category=TrendingCategory.MEME)

    def test_get_trending_terms_user_not_found_defaults_to_free(self, trending_service, sample_trending_term):
        """Test that when user is not found, we default to FREE tier restrictions."""
        # Mock repository response
        trending_service.repository.get_trending_terms.return_value = [sample_trending_term]
        trending_service.repository.get_trending_stats.return_value = {
            "total_terms": 1,
            "active_terms": 1,
            "categories": {"slang": 1}
        }

        # Mock user service to return None (user not found)
        trending_service.user_service.get_user.return_value = None

        # Test with premium-level request
        result = trending_service.get_trending_terms(
            user_id="nonexistent_user_123",
            limit=50,  # Should be limited to 10
            category=TrendingCategory.MEME  # Should be restricted
        )

        # Should be limited to 10 terms max (FREE tier limit)
        trending_service.repository.get_trending_terms.assert_called_with(limit=10, category=None, active_only=True)

        # Should get limited data (FREE tier response)
        assert result.total_count == 1
        assert len(result.terms) == 1
        assert result.terms[0].term == sample_trending_term.term
        assert result.terms[0].search_count == 0  # FREE tier gets limited data
        assert result.terms[0].example_usage == ""  # FREE tier gets limited data
        assert result.terms[0].origin == ""  # FREE tier gets limited data
        assert result.terms[0].related_terms == []  # FREE tier gets limited data

    def test_get_trending_terms_premium_tier_full_access(self, trending_service, sample_trending_term):
        """Test premium tier gets full access to all features."""
        trending_service.repository.get_trending_terms.return_value = [sample_trending_term]
        trending_service.repository.get_trending_stats.return_value = {
            "total_active_terms": 1,
            "last_updated": "2024-01-15T10:00:00Z"
        }

        # Mock user service to return premium user
        from models.users import User, UserTier
        mock_user = User(
            user_id="premium_user_123",
            email="premium@example.com",
            username="premium_user",
            tier=UserTier.PREMIUM,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        trending_service.user_service.get_user.return_value = mock_user

        result = trending_service.get_trending_terms(
            user_id="premium_user_123",
            limit=100,
            category=TrendingCategory.MEME
        )

        # Premium should get full data
        assert result.terms[0].search_count == sample_trending_term.search_count
        assert result.terms[0].example_usage == sample_trending_term.example_usage
        assert result.terms[0].origin == sample_trending_term.origin
        assert result.terms[0].related_terms == sample_trending_term.related_terms

    def test_get_trending_term_success(self, trending_service, sample_trending_term):
        """Test getting a single trending term."""
        trending_service.repository.get_trending_term.return_value = sample_trending_term

        result = trending_service.get_trending_term("no cap")

        assert result is not None
        assert result.term == sample_trending_term.term
        trending_service.repository.get_trending_term.assert_called_once_with("no cap")

    def test_get_trending_term_not_found(self, trending_service):
        """Test getting a non-existent trending term."""
        trending_service.repository.get_trending_term.return_value = None

        result = trending_service.get_trending_term("nonexistent")

        assert result is None

    def test_create_trending_term_success(self, trending_service, sample_trending_term):
        """Test creating a new trending term."""
        trending_service.repository.get_trending_term.return_value = None  # Term doesn't exist
        trending_service.repository.create_trending_term.return_value = True

        result = trending_service.create_trending_term(sample_trending_term)

        assert result is True
        trending_service.repository.create_trending_term.assert_called_once_with(sample_trending_term)

    def test_create_trending_term_already_exists(self, trending_service, sample_trending_term):
        """Test creating a trending term that already exists."""
        trending_service.repository.get_trending_term.return_value = sample_trending_term

        with pytest.raises(ValidationError, match="Trending term 'no cap' already exists"):
            trending_service.create_trending_term(sample_trending_term)

    def test_create_trending_term_invalid_score(self, trending_service):
        """Test creating a trending term with invalid popularity score."""
        invalid_term = TrendingTerm(
            term="test",
            definition="test definition",
            category=TrendingCategory.SLANG,
            popularity_score=150.0,  # Invalid: > 100
            search_count=0,
            translation_count=0,
            first_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            is_active=True
        )

        with pytest.raises(ValidationError, match="Popularity score must be between 0 and 100"):
            trending_service.create_trending_term(invalid_term)

    def test_update_trending_term_success(self, trending_service, sample_trending_term):
        """Test updating a trending term."""
        trending_service.repository.get_trending_term.return_value = sample_trending_term
        trending_service.repository.update_trending_term.return_value = True

        updated_term = sample_trending_term.model_copy()
        updated_term.definition = "Updated definition"

        result = trending_service.update_trending_term(updated_term)

        assert result is True
        trending_service.repository.update_trending_term.assert_called_once_with(updated_term)

    def test_update_trending_term_not_found(self, trending_service, sample_trending_term):
        """Test updating a non-existent trending term."""
        trending_service.repository.get_trending_term.return_value = None

        with pytest.raises(ValidationError, match="Trending term 'no cap' not found"):
            trending_service.update_trending_term(sample_trending_term)

    def test_increment_search_count(self, trending_service):
        """Test incrementing search count for a trending term."""
        trending_service.repository.increment_search_count.return_value = True

        result = trending_service.increment_search_count("no cap")

        assert result is True
        trending_service.repository.increment_search_count.assert_called_once_with("no cap")

    def test_increment_translation_count(self, trending_service):
        """Test incrementing translation count for a trending term."""
        trending_service.repository.increment_translation_count.return_value = True

        result = trending_service.increment_translation_count("no cap")

        assert result is True
        trending_service.repository.increment_translation_count.assert_called_once_with("no cap")

    def test_run_trending_job_success(self, trending_service, sample_trending_job_request):
        """Test running trending job successfully."""
        # Mock Bedrock response
        mock_bedrock_response = {
            "body": Mock()
        }
        mock_bedrock_response["body"].read.return_value = b'{"content": [{"text": "[{\\"term\\": \\"test\\", \\"definition\\": \\"test def\\", \\"category\\": \\"slang\\", \\"popularity_score\\": 85.0}]"}]}'

        trending_service.bedrock_client.invoke_model.return_value = mock_bedrock_response

        # Mock repository methods
        trending_service.repository.get_trending_term.return_value = None  # New term
        trending_service.repository.create_trending_term.return_value = True
        trending_service.repository.get_trending_stats.return_value = {
            "total_active_terms": 1,
            "last_updated": "2024-01-15T10:00:00Z"
        }

        result = trending_service.run_trending_job(sample_trending_job_request)

        assert result.status == "completed"
        assert result.terms_processed > 0
        assert result.terms_added > 0
        assert result.error_message is None
        assert result.completed_at is not None

    def test_run_trending_job_bedrock_failure(self, trending_service, sample_trending_job_request):
        """Test trending job when Bedrock fails."""
        # Mock Bedrock failure
        trending_service.bedrock_client.invoke_model.side_effect = Exception("Bedrock error")

        result = trending_service.run_trending_job(sample_trending_job_request)

        assert result.status == "failed"
        assert result.error_message == "Bedrock error"
        assert result.completed_at is None

    def test_generate_trending_terms_with_bedrock_success(self, trending_service):
        """Test Bedrock trending terms generation success."""
        # Mock Bedrock response
        mock_bedrock_response = {
            "body": Mock()
        }
        mock_bedrock_response["body"].read.return_value = b'{"content": [{"text": "[{\\"term\\": \\"test\\", \\"definition\\": \\"test def\\", \\"category\\": \\"slang\\", \\"popularity_score\\": 85.0, \\"example_usage\\": \\"test example\\", \\"origin\\": \\"test origin\\", \\"related_terms\\": [\\"related\\"]}]"}]}'

        trending_service.bedrock_client.invoke_model.return_value = mock_bedrock_response

        result = trending_service._generate_trending_terms_with_bedrock()

        assert len(result) == 1
        assert result[0]["term"] == "test"
        assert result[0]["definition"] == "test def"
        assert result[0]["category"] == TrendingCategory.SLANG
        assert result[0]["popularity_score"] == 85.0

    def test_generate_trending_terms_with_bedrock_fallback(self, trending_service):
        """Test Bedrock trending terms generation fallback to sample terms."""
        # Mock Bedrock failure
        trending_service.bedrock_client.invoke_model.side_effect = Exception("Bedrock error")

        result = trending_service._generate_trending_terms_with_bedrock()

        # Should return fallback terms
        assert len(result) > 0
        assert result[0]["term"] == "no cap"  # First fallback term

    def test_parse_bedrock_trending_response_success(self, trending_service):
        """Test parsing Bedrock response successfully."""
        response_text = '[{"term": "test", "definition": "test def", "category": "slang", "popularity_score": 85.0}]'

        result = trending_service._parse_bedrock_trending_response(response_text)

        assert len(result) == 1
        assert result[0]["term"] == "test"
        assert result[0]["category"] == TrendingCategory.SLANG

    def test_parse_bedrock_trending_response_invalid_json(self, trending_service):
        """Test parsing invalid Bedrock response falls back to sample terms."""
        invalid_response = "This is not valid JSON"

        result = trending_service._parse_bedrock_trending_response(invalid_response)

        # Should return fallback terms
        assert len(result) > 0
        assert result[0]["term"] == "no cap"

    def test_validate_trending_term_data_success(self, trending_service):
        """Test validating trending term data with all required fields."""
        term_data = {
            "term": "test",
            "definition": "test definition",
            "category": "slang",
            "popularity_score": 85.0
        }

        result = trending_service._validate_trending_term_data(term_data)

        assert result is True

    def test_validate_trending_term_data_missing_fields(self, trending_service):
        """Test validating trending term data with missing required fields."""
        term_data = {
            "term": "test",
            "definition": "test definition"
            # Missing category and popularity_score
        }

        result = trending_service._validate_trending_term_data(term_data)

        assert result is False
