"""Translation service with AWS Bedrock integration."""

import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from models.translations import (
    TranslationRequestInternal,
    Translation,
    TranslationHistory,
    TranslationHistoryServiceResult,
    TranslationDirection,
    BedrockResponse,
)

from utils.logging import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service, BedrockConfig, UsageLimitsConfig
from utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    SystemError,
    UsageLimitExceededError,
    InsufficientPermissionsError,
)
from repositories.translation_repository import TranslationRepository
from services.user_service import UserService


class TranslationService:
    """Service for Lingible translation using AWS Bedrock."""

    def __init__(self) -> None:
        """Initialize translation service."""
        self.config_service = get_config_service()
        self.bedrock_client = aws_services.bedrock_client
        self.translation_repository = TranslationRepository()
        self.user_service = UserService()
        self.bedrock_config = self.config_service.get_config(BedrockConfig)
        self.usage_config = self.config_service.get_config(UsageLimitsConfig)



    @tracer.trace_method("translate_text")
    def translate_text(
        self, request: TranslationRequestInternal, user_id: str
    ) -> Translation:
        """Translate text using AWS Bedrock."""
        start_time = time.time()
        translation_id = self.translation_repository.generate_translation_id()

        try:
            # Validate request
            self._validate_translation_request(request)

            # Check usage limits first
            usage_response = self.user_service.get_user_usage(user_id)
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

            # Generate Bedrock prompt
            prompt = self._generate_bedrock_prompt(request)

            # Call Bedrock API
            bedrock_response = self._call_bedrock_api(prompt)

            # Parse and validate response
            translated_text = self._parse_bedrock_response(
                bedrock_response, request.direction
            )

            # Validate that we got an actual translation, not the same text
            if self._is_same_text(translated_text, request.text):
                logger.log_business_event(
                    "model_returned_same_text",
                    {
                        "original_text": request.text,
                        "translated_text": translated_text,
                        "direction": request.direction.value,
                    }
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
                confidence_score=self._calculate_confidence_score(bedrock_response),
                translation_id=translation_id,
                created_at=datetime.now(timezone.utc),
                processing_time_ms=processing_time_ms,
                model_used=self.bedrock_config.model,
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
        self, request: TranslationRequestInternal
    ) -> None:
        """Validate translation request."""
        if not request.text or not request.text.strip():
            raise ValidationError("Text cannot be empty")

        if len(request.text) > 1000:
            raise ValidationError("Text exceeds maximum length of 1000 characters")

    def _generate_bedrock_prompt(self, request: TranslationRequestInternal) -> str:
        """Generate prompt for Bedrock API (Messages API format)."""
        direction = request.direction
        text = request.text

        if direction == TranslationDirection.GENZ_TO_ENGLISH:
            prompt = f"""You are a GenZ translator. Translate this GenZ/internet slang to natural, everyday English.

Text: "{text}"

Rules:
- Give ONE direct, natural translation that sounds like how someone would actually say it
- Don't explain what the slang means, just translate it naturally
- Keep the same tone and energy level
- Use casual, conversational English
- Provide only the translated text, nothing else
- NEVER return the same text - always provide an actual translation
- If you're unsure, make your best guess rather than returning the original

Examples:
- "no cap" → "for real"
- "it's giving main character energy" → "that person has an exceptionally confident and self-assured presence"
- "that's fire" → "that's amazing"
- "bet" → "okay"
- "periodt" → "exactly"

Translate:"""
        else:
            prompt = f"""You are a GenZ translator. Translate this standard English to natural GenZ/internet slang.

Text: "{text}"

Rules:
- Use authentic GenZ slang that people actually say
- Keep the same meaning and energy level
- Make it sound natural and current
- Don't over-explain or be too formal
- Provide only the translated text, nothing else
- NEVER return the same text - always provide an actual translation
- If you're unsure, make your best guess rather than returning the original

Examples:
- "that's really good" → "that's fire"
- "that person has an exceptionally confident and self-assured presence" → "it's giving main character energy"
- "for real" → "no cap"
- "okay" → "bet"
- "exactly" → "periodt"

Translate:"""

        return prompt

    @tracer.trace_external_call("bedrock", "invoke")
    def _call_bedrock_api(self, prompt: str) -> BedrockResponse:
        """Call AWS Bedrock API using Messages API format for Claude 3."""
        try:
            # Claude 3 models use the Messages API format
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.bedrock_config.max_tokens,
                "temperature": self.bedrock_config.temperature,
                "top_p": 0.9,  # Not in config model, hardcoded
                "anthropic_version": "bedrock-2023-05-31"
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_config.model,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())

            # Extract the text content from Messages API response
            content = response_body.get("content", [])
            completion_text = ""
            if content and len(content) > 0:
                completion_text = content[0].get("text", "")

            return BedrockResponse(
                completion=completion_text,
                stop_reason=response_body.get("stop_reason"),
                usage=response_body.get("usage"),
            )

        except Exception as e:
            logger.log_error(e, {"operation": "bedrock_api_call"})
            raise SystemError(f"Failed to call Bedrock API: {str(e)}")

    def _parse_bedrock_response(
        self, response: BedrockResponse, direction: TranslationDirection
    ) -> str:
        """Parse and validate Bedrock response."""
        completion = response.completion.strip()

        if not completion:
            raise BusinessLogicError("Bedrock returned empty response")

        # Clean up the response (remove any extra formatting)
        if completion.startswith('"') and completion.endswith('"'):
            completion = completion[1:-1]

        # Remove common prefixes that might be added
        prefixes_to_remove = [
            "Translation:",
            "translation:",
            "Translated:",
            "translated:",
            "Answer:",
            "answer:",
            "Result:",
            "result:",
        ]

        for prefix in prefixes_to_remove:
            if completion.lower().startswith(prefix.lower()):
                completion = completion[len(prefix):].strip()
                break

        # Remove any trailing punctuation that might be added by the model
        if completion.endswith('.') and not completion.endswith('...'):
            # Only remove single periods, not ellipses
            completion = completion[:-1]

        if not completion:
            raise BusinessLogicError("Invalid response format from Bedrock")

        return completion

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
        clean_translated = re.sub(r'[^\w\s]', '', normalized_translated)
        clean_original = re.sub(r'[^\w\s]', '', normalized_original)

        if clean_translated == clean_original:
            return True

        return False

    def _calculate_confidence_score(self, response: BedrockResponse) -> Optional[Decimal]:
        """Calculate confidence score based on response quality."""
        # Simple heuristic - in production, you might use more sophisticated analysis
        completion = response.completion.strip()

        if not completion:
            return Decimal("0.0")

        # Basic confidence based on response length and content
        if len(completion) < 3:
            return Decimal("0.3")
        elif len(completion) > 50:
            return Decimal("0.9")
        else:
            return Decimal("0.7")

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
    def delete_user_translations(self, user_id: str, is_account_deletion: bool = False) -> int:
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
