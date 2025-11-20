"""Tests for service layer."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.translations import (
    Translation,
    TranslationDirection,
    TranslationRequest,
    TranslationRequestInternal,
)
from models.users import User, UserTier, UserStatus, UserUsageResponse
from models.subscriptions import (
    UserSubscription,
    SubscriptionStatus,
    SubscriptionProvider,
    TransactionData,
    ReceiptValidationStatus,
    StoreEnvironment,
)
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
        with patch('services.translation_service.get_config_service') as mock_get_config, \
             patch('services.translation_service.TranslationRepository') as mock_repo_class, \
             patch('services.translation_service.UserService') as mock_user_service_class, \
             patch('services.translation_service.SlangService') as mock_slang_service_class:
            mock_get_config.return_value = mock_config

            mock_repo = Mock()
            mock_repo.generate_translation_id.return_value = "trans_1"
            mock_repo.create_translation.return_value = True
            mock_repo_class.return_value = mock_repo

            mock_user_service = Mock()
            mock_user_service.get_user_usage.return_value = UserUsageResponse(
                tier=UserTier.FREE,
                daily_limit=10,
                daily_used=0,
                daily_remaining=10,
                reset_date=datetime.now(timezone.utc),
                current_max_text_length=100,
                free_tier_max_length=100,
                premium_tier_max_length=500,
                free_daily_limit=10,
                premium_daily_limit=100,
            )
            mock_user_service_class.return_value = mock_user_service

            mock_slang_service = Mock()
            mock_slang_service.config.model = "anthropic.claude-3-haiku-20240307-v1:0"
            mock_slang_service.config.low_confidence_threshold = Decimal("0.3")
            mock_slang_service.translate_to_english.return_value.translated = "Hello world"
            mock_slang_service.translate_to_english.return_value.confidence = Decimal("0.8")
            mock_slang_service.translate_to_genz.return_value.translated = "Hola mundo"
            mock_slang_service.translate_to_genz.return_value.confidence = Decimal("0.8")
            mock_slang_service_class.return_value = mock_slang_service

            service = TranslationService()
            service.translation_repository = mock_repo
            service.user_service = mock_user_service
            service.slang_service = mock_slang_service
            return service

    def test_translate_english_to_genz(self, translation_service, sample_user):
        """Test translation from English to GenZ."""
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_user.user_id,
        )

        translation_service.translation_repository.generate_translation_id.return_value = "trans_100"

        result = translation_service.translate_text(request, sample_user.user_id)

        assert result.translation_id == "trans_100"
        assert result.original_text == "Hello world"
        assert result.translated_text == "Hola mundo"
        assert result.direction == TranslationDirection.ENGLISH_TO_GENZ
        assert result.confidence_score == Decimal("0.8")

    def test_translate_genz_to_english(self, translation_service, sample_user):
        """Test translation from GenZ to English."""
        request = TranslationRequestInternal(
            text="Hola mundo",
            direction=TranslationDirection.GENZ_TO_ENGLISH,
            user_id=sample_user.user_id,
        )

        translation_service.translation_repository.generate_translation_id.return_value = "trans_101"
        translation_service.slang_service.translate_to_english.return_value.translated = "Hello world"
        translation_service.slang_service.translate_to_english.return_value.confidence = Decimal("0.8")

        result = translation_service.translate_text(request, sample_user.user_id)

        assert result.translation_id == "trans_101"
        assert result.original_text == "Hola mundo"
        assert result.translated_text == "Hello world"
        assert result.direction == TranslationDirection.GENZ_TO_ENGLISH

    def test_translate_with_empty_text(self, translation_service, sample_user):
        """Test translation with empty text raises error."""
        request = TranslationRequestInternal(
            text="   ",  # whitespace should trigger validation inside service
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_user.user_id,
        )

        with pytest.raises(ValidationError):
            translation_service.translate_text(request, sample_user.user_id)

    def test_translate_with_long_text(self, translation_service, sample_user):
        """Test translation with text exceeding limit raises error."""
        long_text = "x" * 101  # Exceeds 100 character limit for premium
        request = TranslationRequestInternal(
            text=long_text,
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_user.user_id,
        )

        with pytest.raises(ValidationError):
            translation_service.translate_text(request, sample_user.user_id)

    def test_bedrock_api_error_handling(self, translation_service, sample_user, mock_bedrock_client):
        """Test handling of Bedrock API errors."""
        # Simulate slang translation failure
        translation_service.slang_service.translate_to_genz.side_effect = Exception("API Error")

        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_user.user_id,
        )

        with pytest.raises(Exception):
            translation_service.translate_text(request, sample_user.user_id)

    def test_translation_history_storage_premium_user(self, translation_service, sample_premium_user):
        """Test that translations are stored for premium users."""
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_premium_user.user_id,
        )

        translation_service.user_service.get_user_usage.return_value = UserUsageResponse(
            tier=UserTier.PREMIUM,
            daily_limit=100,
            daily_used=5,
            daily_remaining=95,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=500,
            free_tier_max_length=100,
            premium_tier_max_length=500,
            free_daily_limit=10,
            premium_daily_limit=100,
        )
        translation_service.translation_repository.generate_translation_id.return_value = "trans_premium"

        with patch.object(translation_service, '_save_translation_history') as mock_save:
            translation_service.translate_text(request, sample_premium_user.user_id)
            mock_save.assert_called_once()

    def test_translation_history_not_stored_free_user(self, translation_service, sample_user):
        """Test that translations are not stored for free users."""
        request = TranslationRequestInternal(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            user_id=sample_user.user_id,
        )

        translation_service.translation_repository.generate_translation_id.return_value = "trans_free"

        with patch.object(translation_service, '_save_translation_history') as mock_save:
            translation_service.translate_text(request, sample_user.user_id)
            mock_save.assert_called_once()

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

        translation_service.user_service.get_user_usage.return_value = usage_response

        with pytest.raises(UsageLimitExceededError) as exc_info:
            translation_service.translate_text(request, user_id)

        exception = exc_info.value
        assert "daily" in exception.message
        assert exception.status_code == 429
        assert exception.error_code == "BIZ_001"
        translation_service.user_service.increment_usage.assert_not_called()

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
            premium_daily_limit=100,
        )

        mock_response_body = Mock()
        mock_response_body.read.return_value = '{"content": [{"text": "Yo, wassup world!"}], "usage": {"input_tokens": 5, "output_tokens": 8}}'
        mock_bedrock_client.invoke_model.return_value = {"body": mock_response_body}

        translation_service.user_service.get_user_usage.return_value = usage_response
        translation_service.translation_repository.generate_translation_id.return_value = "trans_123"
        translation_service.translation_repository.create_translation.return_value = True
        translation_service.slang_service.translate_to_genz.return_value.translated = "Yo, wassup world!"

        result = translation_service.translate_text(request, user_id)

        assert result is not None
        assert result.translated_text == "Yo, wassup world!"
        translation_service.user_service.increment_usage.assert_called_once_with(user_id, UserTier.FREE)

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
            premium_daily_limit=100,
        )

        translation_service.user_service.get_user_usage.return_value = usage_response
        translation_service.slang_service.translate_to_genz.side_effect = Exception("translation failure")

        with pytest.raises(Exception):
            translation_service.translate_text(request, user_id)

        translation_service.user_service.increment_usage.assert_not_called()
        translation_service.slang_service.translate_to_genz.side_effect = None

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

        translation_service.user_service.get_user_usage.return_value = usage_response
        translation_service.translation_repository.generate_translation_id.return_value = "trans_123"
        translation_service.translation_repository.create_translation.return_value = True
        translation_service.slang_service.translate_to_genz.return_value = slang_result
        translation_service.slang_service.config.low_confidence_threshold = Decimal("0.3")

        result = translation_service.translate_text(request, user_id)

        from utils.translation_messages import TranslationMessages

        assert result.translation_failed is True
        assert result.failure_reason == "low_confidence"
        assert result.user_message in TranslationMessages.LOW_CONFIDENCE
        translation_service.user_service.increment_usage.assert_not_called()
        assert result.daily_used == usage_response.daily_used
        translation_service.translation_repository.create_translation.assert_not_called()
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

        translation_service.user_service.get_user_usage.return_value = usage_response
        translation_service.translation_repository.generate_translation_id.return_value = "trans_456"
        translation_service.translation_repository.create_translation.return_value = True
        translation_service.slang_service.translate_to_english.return_value = slang_result
        translation_service.slang_service.config.low_confidence_threshold = Decimal("0.3")

        result = translation_service.translate_text(request, user_id)

        from utils.translation_messages import TranslationMessages

        assert result.translation_failed is True
        assert result.failure_reason == "no_translation_needed"
        assert result.user_message in TranslationMessages.NO_TRANSLATION_GENZ_TO_ENGLISH
        translation_service.user_service.increment_usage.assert_not_called()

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
        import os
        env_defaults = {
            "USERS_TABLE": "test-users-table",
            "FREE_DAILY_TRANSLATIONS": "10",
            "PREMIUM_DAILY_TRANSLATIONS": "100",
            "FREE_MAX_TEXT_LENGTH": "100",
            "PREMIUM_MAX_TEXT_LENGTH": "500",
            "FREE_HISTORY_RETENTION_DAYS": "7",
            "PREMIUM_HISTORY_RETENTION_DAYS": "90",
        }
        for key, value in env_defaults.items():
            os.environ.setdefault(key, value)
        with patch('src.services.user_service.get_config_service', return_value=mock_config):
            with patch('src.services.user_service.UserRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo
                service = UserService()
                service.repository = mock_repo
                service.user_repository = mock_repo
                service.config_service = mock_config
                return service

    def test_get_user(self, user_service, sample_user):
        """Test getting user profile details."""
        user_service.user_repository.get_user.return_value = sample_user

        result = user_service.get_user("test_user_123")

        assert result == sample_user
        user_service.user_repository.get_user.assert_called_once_with("test_user_123")

    def test_get_user_not_found(self, user_service):
        """Test getting a user that doesn't exist."""
        user_service.user_repository.get_user.return_value = None

        result = user_service.get_user("nonexistent_user")

        assert result is None

    def test_get_user_usage(self, user_service, sample_user):
        """Test getting user usage statistics."""
        user_service.user_repository.get_user.return_value = sample_user
        from datetime import datetime, timezone, timedelta
        from models.translations import UsageLimit

        usage_limit = UsageLimit(
            tier=UserTier.FREE,
            daily_used=7,
            reset_daily_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        user_service.user_repository.get_usage_limits.return_value = usage_limit

        result = user_service.get_user_usage("test_user_123")

        assert result.daily_limit == user_service.usage_config.free_daily_translations
        assert result.daily_used == 7
        assert result.daily_limit == user_service.usage_config.free_daily_translations
        assert result.tier == UserTier.FREE

    def test_upgrade_user_tier_to_premium(self, user_service, sample_user):
        """Test upgrading user tier to premium."""
        from datetime import datetime, timezone
        from unittest.mock import Mock

        user_service.user_repository.get_user.return_value = sample_user
        user_service.user_repository.update_user.return_value = True
        # Mock usage limits
        user_service.user_repository.get_usage_limits.return_value = Mock(tier=UserTier.FREE)
        user_service.user_repository.update_usage_limits.return_value = True
        # Mock quiz limit deletion
        user_service.user_repository.delete_daily_quiz_count.return_value = True

        user_service.upgrade_user_tier("test_user_123", UserTier.PREMIUM)
        # Verify the user tier was updated
        user_service.user_repository.update_user.assert_called_once()
        updated_user = user_service.user_repository.update_user.call_args[0][0]
        assert updated_user.tier == UserTier.PREMIUM
        # Verify quiz daily count item was deleted via repository method
        user_service.user_repository.delete_daily_quiz_count.assert_called_once_with("test_user_123")

    def test_upgrade_user_tier_to_premium_quiz_reset_handles_error(self, user_service, sample_user):
        """Test upgrade_user_tier handles quiz limit deletion errors gracefully."""
        from datetime import datetime, timezone
        from unittest.mock import Mock

        user_service.user_repository.get_user.return_value = sample_user
        user_service.user_repository.update_user.return_value = True
        user_service.user_repository.get_usage_limits.return_value = Mock(tier=UserTier.FREE)
        user_service.user_repository.update_usage_limits.return_value = True
        # Mock repository deletion failure (returns False)
        user_service.user_repository.delete_daily_quiz_count.return_value = False

        # Should still succeed even if quiz deletion fails
        user_service.upgrade_user_tier("test_user_123", UserTier.PREMIUM)
        user_service.user_repository.update_user.assert_called_once()
        # Verify the method was called even though it failed
        user_service.user_repository.delete_daily_quiz_count.assert_called_once_with("test_user_123")

    def test_upgrade_user_tier_to_free_no_quiz_reset(self, user_service, sample_user):
        """Test upgrading to FREE tier doesn't delete quiz count."""
        from unittest.mock import Mock

        user_service.user_repository.get_user.return_value = sample_user
        user_service.user_repository.update_user.return_value = True
        user_service.user_repository.get_usage_limits.return_value = Mock(tier=UserTier.PREMIUM)
        user_service.user_repository.update_usage_limits.return_value = True

        user_service.upgrade_user_tier("test_user_123", UserTier.FREE)
        # Should not delete quiz count when downgrading to FREE
        user_service.user_repository.delete_daily_quiz_count.assert_not_called()

    def test_upgrade_user_tier_nonexistent_user(self, user_service):
        """Test upgrading tier for user that doesn't exist."""
        user_service.user_repository.get_user.return_value = None

        with pytest.raises(ValidationError):
            user_service.upgrade_user_tier("nonexistent_user", UserTier.PREMIUM)

    def test_delete_user_deletes_quiz_data(self, user_service):
        """Test delete_user calls quiz data cleanup before deleting user."""
        from unittest.mock import Mock, patch

        user_service.user_repository.delete_all_quiz_data.return_value = None
        user_service.user_repository.delete_user.return_value = True

        with patch('src.services.user_service.get_cognito_client') as mock_cognito:
            mock_cognito_client = Mock()
            mock_cognito.return_value = mock_cognito_client
            user_service.config_service = Mock()
            user_service.config_service.get_config.return_value = Mock(user_pool_id="pool_123")

            user_service.delete_user("user_123")

            user_service.user_repository.delete_all_quiz_data.assert_called_once_with("user_123")
            user_service.user_repository.delete_user.assert_called_once_with("user_123")

    # Removed legacy tests relying on deprecated user service methods.


class TestSubscriptionService:
    """Test SubscriptionService."""

    @pytest.fixture
    def subscription_service(self, mock_config):
        """Create SubscriptionService with mocked dependencies."""
        with patch.dict(os.environ, {"USERS_TABLE": "test-users-table"}), \
             patch('services.subscription_service.SubscriptionRepository') as mock_repo_class, \
             patch('services.subscription_service.AppleStoreKitService') as mock_apple_service_class, \
             patch('aws_lambda_powertools.utilities.parameters.secrets.get_secret', return_value='{"privateKey": "fake"}'):
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_apple_service = Mock()
            mock_apple_service_class.return_value = mock_apple_service

            service = SubscriptionService()
            service.subscription_repository = mock_repo
            service.apple_storekit_service = mock_apple_service
            return service

    def test_get_active_subscription(self, subscription_service, sample_subscription):
        """Test retrieving an active subscription."""
        subscription_service.subscription_repository.get_active_subscription.return_value = sample_subscription

        result = subscription_service.get_active_subscription("premium_user_456")

        assert result == sample_subscription
        subscription_service.subscription_repository.get_active_subscription.assert_called_once_with("premium_user_456")

    def test_get_active_subscription_not_found(self, subscription_service):
        """Test retrieving an active subscription when none exists."""
        subscription_service.subscription_repository.get_active_subscription.return_value = None

        result = subscription_service.get_active_subscription("free_user_123")

        assert result is None

    def test_validate_and_create_subscription(self, subscription_service):
        """Test validating and creating a subscription via StoreKit."""
        from datetime import datetime, timezone, timedelta

        transaction_data = TransactionData(
            provider=SubscriptionProvider.APPLE,
            transaction_id="txn_123",
            product_id="premium_monthly",
            purchase_date=datetime.now(timezone.utc),
            expiration_date=datetime.now(timezone.utc) + timedelta(days=30),
            environment=StoreEnvironment.SANDBOX,
        )

        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.status = ReceiptValidationStatus.VALID
        validation_result.transaction_data = transaction_data
        subscription_service.apple_storekit_service.validate_transaction.return_value = validation_result
        subscription_service.subscription_repository.create_subscription.return_value = True

        subscription_service.validate_and_create_subscription("premium_user_456", transaction_data)

        subscription_service.apple_storekit_service.validate_transaction.assert_called_once()
        created_subscription = subscription_service.subscription_repository.create_subscription.call_args[0][0]
        assert created_subscription.user_id == "premium_user_456"
        assert created_subscription.transaction_id == transaction_data.transaction_id

    def test_validate_and_create_subscription_invalid_transaction(self, subscription_service):
        """Test validation failure raises ValidationError."""
        from datetime import datetime, timezone

        transaction_data = TransactionData(
            provider=SubscriptionProvider.APPLE,
            transaction_id="txn_invalid",
            product_id="premium_monthly",
            purchase_date=datetime.now(timezone.utc),
            expiration_date=None,
            environment=StoreEnvironment.PRODUCTION,
        )

        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.status = ReceiptValidationStatus.ALREADY_USED
        validation_result.transaction_data = transaction_data
        validation_result.error_message = "Already used"
        subscription_service.apple_storekit_service.validate_transaction.return_value = validation_result

        with pytest.raises(ValidationError):
            subscription_service.validate_and_create_subscription("premium_user_456", transaction_data)

        subscription_service.subscription_repository.create_subscription.assert_not_called()

    def test_cancel_subscription(self, subscription_service):
        """Test canceling a subscription succeeds."""
        subscription_service.subscription_repository.cancel_subscription.return_value = True

        subscription_service.cancel_subscription("premium_user_456")

        subscription_service.subscription_repository.cancel_subscription.assert_called_once_with("premium_user_456")

    def test_cancel_subscription_failure_raises(self, subscription_service):
        """Test canceling a subscription raises when repository fails."""
        subscription_service.subscription_repository.cancel_subscription.return_value = False

        with pytest.raises(BusinessLogicError):
            subscription_service.cancel_subscription("premium_user_456")

    def test_find_user_id_by_transaction_id(self, subscription_service, sample_subscription):
        """Test mapping transaction ID to user ID."""
        subscription_service.subscription_repository.find_by_transaction_id.return_value = sample_subscription

        result = subscription_service.find_user_id_by_transaction_id("txn_123")

        assert result == sample_subscription.user_id
        subscription_service.subscription_repository.find_by_transaction_id.assert_called_once_with("txn_123")

    def test_find_user_id_by_transaction_id_not_found(self, subscription_service):
        """Test mapping transaction ID returns None when subscription missing."""
        subscription_service.subscription_repository.find_by_transaction_id.return_value = None

        result = subscription_service.find_user_id_by_transaction_id("txn_missing")

        assert result is None


class TestTrendingService:
    """Test TrendingService with comprehensive unit tests."""

    @pytest.fixture
    def trending_service(self, mock_bedrock_client, mock_config):
        """Create TrendingService with mocked dependencies."""
        with patch.dict(os.environ, {"TERMS_TABLE": "test-terms-table"}), \
             patch('services.trending_service.TrendingRepository') as mock_repo_class, \
             patch('services.trending_service.aws_services') as mock_aws_services, \
             patch('services.trending_service.get_config_service') as mock_get_config, \
             patch('services.trending_service.UserService') as mock_user_service_class:
            mock_repo = Mock()
            mock_repo.get_trending_stats.return_value = {"total_active_terms": 0}
            mock_repo.get_trending_terms.return_value = []
            mock_repo.get_trending_term.return_value = None
            mock_repo.create_trending_term.return_value = True
            mock_repo.update_trending_term.return_value = True
            mock_repo.increment_search_count.return_value = True
            mock_repo.increment_translation_count.return_value = True
            mock_repo_class.return_value = mock_repo
            mock_aws_services.bedrock_client = mock_bedrock_client
            mock_get_config.return_value = mock_config
            mock_config._get_env_var.side_effect = lambda key: {
                "TERMS_TABLE": "test-terms-table"
            }.get(key, f"mock-{key.lower()}")

            from models.config import LLMConfig

            def mock_get_config_method(config_type, table_name=None):
                if config_type == LLMConfig:
                    return LLMConfig(
                        model="anthropic.claude-3-sonnet-20240229-v1:0",
                        max_tokens=1000,
                        temperature=0.7,
                        top_p=0.9,
                        low_confidence_threshold=0.3,
                        lexicon_s3_bucket="test-bucket",
                        lexicon_s3_key="test-key",
                        age_max_rating="M18",
                        age_filter_mode="skip",
                    )
                return mock_config.get_config(config_type, table_name)

            mock_config.get_config.side_effect = mock_get_config_method

            mock_user_service = Mock()
            mock_user_service_class.return_value = mock_user_service

            service = TrendingService()
            service.repository = mock_repo
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

        # Should raise validation error due to restricted category for default FREE tier
        with pytest.raises(ValidationError, match="Category filtering is a premium feature"):
            trending_service.get_trending_terms(
                user_id="nonexistent_user_123",
                limit=50,
                category=TrendingCategory.MEME,
            )

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
        trending_service.repository.get_trending_term.return_value = None
        trending_service.repository.create_trending_term.return_value = True

        result = trending_service.create_trending_term(
            term="yeet",
            definition="To throw with force",
            category=TrendingCategory.SLANG,
            popularity_score=Decimal("82.5"),
            example_usage="Yeet that ball across the field",
            origin="Internet slang",
            related_terms=["throw", "toss"],
        )

        assert isinstance(result, TrendingTerm)
        assert result.term == "yeet"
        trending_service.repository.create_trending_term.assert_called_once()

    def test_create_trending_term_already_exists(self, trending_service, sample_trending_term):
        """Test creating a trending term that already exists."""
        trending_service.repository.get_trending_term.return_value = sample_trending_term

        with pytest.raises(ValidationError, match="Trending term 'no cap' already exists"):
            trending_service.create_trending_term(
                term=sample_trending_term.term,
                definition=sample_trending_term.definition,
                category=sample_trending_term.category,
                popularity_score=sample_trending_term.popularity_score,
            )

    def test_create_trending_term_invalid_score(self, trending_service):
        """Test creating a trending term with invalid popularity score."""
        trending_service.repository.get_trending_term.return_value = None

        with pytest.raises(ValidationError, match="Popularity score must be between 0 and 100"):
            trending_service.create_trending_term(
                term="test",
                definition="test definition",
                category=TrendingCategory.SLANG,
                popularity_score=150.0,
            )

    def test_update_trending_term_success(self, trending_service, sample_trending_term):
        """Test updating a trending term."""
        trending_service.repository.get_trending_term.return_value = sample_trending_term
        trending_service.repository.update_trending_term.return_value = True

        result = trending_service.update_trending_term(
            term=sample_trending_term.term,
            definition="Updated definition",
            popularity_score=Decimal("90.0"),
            is_active=False,
        )

        assert isinstance(result, TrendingTerm)
        assert result.definition == "Updated definition"
        assert result.popularity_score == Decimal("90.0")
        assert result.is_active is False
        trending_service.repository.update_trending_term.assert_called_once()

    def test_update_trending_term_not_found(self, trending_service, sample_trending_term):
        """Test updating a non-existent trending term."""
        trending_service.repository.get_trending_term.return_value = None

        with pytest.raises(ValidationError, match="Trending term 'no cap' not found"):
            trending_service.update_trending_term(
                term=sample_trending_term.term,
                definition="Updated definition",
            )

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

        assert result.status == "completed"
        trending_service.repository.create_trending_term.assert_called()

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
