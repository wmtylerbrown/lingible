"""Translation service for GenZ ↔ English slang translation."""

import re
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from models.translations import (
    TranslationRequestInternal,
    Translation,
    TranslationHistory,
    TranslationHistoryServiceResult,
    TranslationDirection,
)

from utils.smart_logger import logger
from utils.tracing import tracer
from utils.config import get_config_service, UsageLimitsConfig
from utils.exceptions import (
    ValidationError,
    UsageLimitExceededError,
    InsufficientPermissionsError,
)
from repositories.translation_repository import TranslationRepository
from services.user_service import UserService
from services.slang_service import SlangService


class TranslationService:
    """Service for Lingible GenZ ↔ English slang translation."""

    def __init__(self) -> None:
        """Initialize translation service."""
        self.config_service = get_config_service()
        self.translation_repository = TranslationRepository()
        self.user_service = UserService()
        self.usage_config = self.config_service.get_config(UsageLimitsConfig)
        self.slang_service = SlangService()

    @tracer.trace_method("translate_text")
    def translate_text(
        self, request: TranslationRequestInternal, user_id: str
    ) -> Translation:
        """Translate text using AWS Bedrock."""
        start_time = time.time()
        translation_id = self.translation_repository.generate_translation_id()

        try:
            # Check usage limits first to get user's text length limit
            usage_response = self.user_service.get_user_usage(user_id)

            # Validate request with user's tier-specific limits
            self._validate_translation_request(
                request, usage_response.current_max_text_length
            )

            if usage_response.daily_remaining <= 0:
                raise UsageLimitExceededError(
                    "daily",
                    usage_response.daily_used,
                    usage_response.daily_limit,
                )

            # Atomically increment usage (pass tier for consistency)
            self.user_service.increment_usage(user_id, usage_response.tier)

            # Calculate updated usage data for response
            updated_daily_used = usage_response.daily_used + 1
            updated_daily_limit = usage_response.daily_limit
            updated_tier = usage_response.tier

            # Translate using slang service (handles both directions)
            if request.direction == TranslationDirection.GENZ_TO_ENGLISH:
                # GenZ → English: Use slang service
                slang_result = self.slang_service.translate_to_english(request.text)
            elif request.direction == TranslationDirection.ENGLISH_TO_GENZ:
                # English → GenZ: Use slang service
                slang_result = self.slang_service.translate_to_genz(request.text)
            else:
                raise ValidationError(
                    f"Unsupported translation direction: {request.direction}"
                )

            # Extract results from slang translation
            translated_text = slang_result.translated
            confidence_score = slang_result.confidence

            # Validate that we got an actual translation, not the same text
            if self._is_same_text(translated_text, request.text):
                logger.log_business_event(
                    "model_returned_same_text",
                    {
                        "original_text": request.text,
                        "translated_text": translated_text,
                        "direction": request.direction,
                    },
                )
                # For now, we'll still return it but log the issue
                # In production, you might want to retry or use a fallback

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Create response
            response = Translation(
                original_text=request.text,
                translated_text=translated_text,
                direction=request.direction,
                confidence_score=confidence_score,
                translation_id=translation_id,
                created_at=datetime.now(timezone.utc),
                processing_time_ms=processing_time_ms,
                model_used=self.slang_service.config.model,
                daily_used=updated_daily_used,
                daily_limit=updated_daily_limit,
                tier=updated_tier,
            )

            # Save translation history
            self._save_translation_history(response, user_id)

            # Only log errors or exceptional cases, not every successful translation
            # This reduces log volume significantly

            return response

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.log_error(
                e,
                {
                    "translation_id": translation_id,
                    "user_id": user_id,
                    "processing_time_ms": processing_time_ms,
                },
            )
            raise

    def _validate_translation_request(
        self, request: TranslationRequestInternal, max_text_length: int
    ) -> None:
        """Validate translation request."""
        if not request.text or not request.text.strip():
            raise ValidationError("Text cannot be empty")

        if len(request.text) > max_text_length:
            raise ValidationError(
                f"Text exceeds maximum length of {max_text_length} characters"
            )

    def _is_same_text(self, translated_text: str, original_text: str) -> bool:
        """Check if the translated text is essentially the same as the original."""
        # Normalize both texts for comparison
        normalized_translated = translated_text.lower().strip()
        normalized_original = original_text.lower().strip()

        # Check for exact match
        if normalized_translated == normalized_original:
            return True

        # Check for very similar text (e.g., just punctuation differences)
        # Remove common punctuation and compare
        clean_translated = re.sub(r"[^\w\s]", "", normalized_translated)
        clean_original = re.sub(r"[^\w\s]", "", normalized_original)

        if clean_translated == clean_original:
            return True

        return False

    def _save_translation_history(self, response: Translation, user_id: str) -> None:
        """Save translation to history (premium users only)."""
        # Only save translations for premium users
        if not self._is_premium_user(user_id):
            # Don't log every storage skip - it's expected behavior for free users
            return

        history_item = TranslationHistory(
            translation_id=response.translation_id,
            user_id=user_id,
            original_text=response.original_text,
            translated_text=response.translated_text,
            direction=response.direction,
            confidence_score=response.confidence_score,
            created_at=response.created_at,
            model_used=response.model_used,
        )

        success = self.translation_repository.create_translation(history_item)
        if not success:
            logger.log_error(
                Exception("Failed to save translation history"),
                {"translation_id": response.translation_id, "user_id": user_id},
            )

    def _is_premium_user(self, user_id: str) -> bool:
        """Check if user has premium access for translation history."""
        try:
            user = self.user_service.get_user(user_id)
            if user and user.tier in ["premium", "pro"]:
                return True
            return False
        except Exception as e:
            logger.log_error(
                e, {"operation": "check_premium_status", "user_id": user_id}
            )
            # Default to non-premium if we can't determine status
            return False

    def get_translation_history(
        self,
        user_id: str,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> TranslationHistoryServiceResult:
        """Get user's translation history (premium feature)."""
        # Check if user has premium access
        if not self._is_premium_user(user_id):
            raise InsufficientPermissionsError(
                message="Translation history is a premium feature. Upgrade to access your translation history.",
            )

        result = self.translation_repository.get_user_translations(
            user_id, limit, last_evaluated_key
        )

        return TranslationHistoryServiceResult(
            translations=result.items,
            total_count=result.count,
            has_more=result.last_evaluated_key is not None,
            last_evaluated_key=result.last_evaluated_key,
        )

    def delete_translation(self, user_id: str, translation_id: str) -> bool:
        """Delete a translation from history (premium feature)."""
        # Check if user has premium access
        if not self._is_premium_user(user_id):
            raise InsufficientPermissionsError(
                message="Translation history management is a premium feature. Upgrade to manage your translation history.",
            )

        # Attempt to delete the translation
        success = self.translation_repository.delete_translation(
            user_id, translation_id
        )

        if not success:
            # Log the failed deletion attempt for security monitoring
            logger.log_error(
                Exception(
                    "Translation deletion failed - translation not found or access denied"
                ),
                {
                    "operation": "delete_translation",
                    "translation_id": translation_id,
                    "user_id": user_id,
                },
            )

        return success

    @tracer.trace_method("delete_user_translations")
    def delete_user_translations(
        self, user_id: str, is_account_deletion: bool = False
    ) -> int:
        """Delete all translations for a user. Returns number of deleted records."""
        # Check if user has premium access (allow deletion during account closure)
        if not self._is_premium_user(user_id) and not is_account_deletion:
            raise InsufficientPermissionsError(
                message="Translation history management is a premium feature. Upgrade to manage your translation history.",
            )

        try:
            # Get all user translations
            translations = self.translation_repository.get_user_translations(
                user_id, limit=1000
            )
            deleted_count = 0

            # Delete each translation
            for translation in translations.items:
                success = self.translation_repository.delete_translation(
                    user_id, translation.translation_id
                )
                if success:
                    deleted_count += 1

            # Only log significant deletions (more than 10 items)
            if deleted_count > 10:
                logger.log_business_event(
                    "user_translations_deleted",
                    {"user_id": user_id, "deleted_count": deleted_count},
                )

            return deleted_count

        except Exception as e:
            logger.log_error(
                e, {"operation": "delete_user_translations", "user_id": user_id}
            )
            return 0
