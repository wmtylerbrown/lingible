"""Translation service with AWS Bedrock integration."""

import json
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..models.translations import (
    TranslationRequestInternal,
    Translation,
    TranslationHistory,
    TranslationDirection,
    BedrockResponse,
)

from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.aws_services import aws_services
from ..utils.config import get_config
from ..utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    SystemError,
    UsageLimitExceededError,
)
from ..repositories.translation_repository import TranslationRepository
from ..services.user_service import UserService


class TranslationService:
    """Service for GenZ slang translation using AWS Bedrock."""

    def __init__(self) -> None:
        """Initialize translation service."""
        self.config = get_config()
        self.bedrock_client = aws_services.bedrock_client
        self.translation_repository = TranslationRepository()
        self.user_service = UserService()
        self.bedrock_config = self.config.get_bedrock_config()
        self.usage_config = self.config.get_usage_limits()

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

            # Atomically increment usage (no need to pass UsageLimit object)
            self.user_service.increment_usage(user_id, usage_response.tier)

            # Generate Bedrock prompt
            prompt = self._generate_bedrock_prompt(request)

            # Call Bedrock API
            bedrock_response = self._call_bedrock_api(prompt)

            # Parse and validate response
            translated_text = self._parse_bedrock_response(
                bedrock_response, request.direction
            )

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
                model_used=self.bedrock_config["model_id"],
            )

            # Save translation history
            self._save_translation_history(response, user_id)

            logger.log_business_event(
                "translation_completed",
                {
                    "translation_id": translation_id,
                    "user_id": user_id,
                    "direction": request.direction.value,
                    "processing_time_ms": processing_time_ms,
                },
            )

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
        """Generate prompt for Bedrock API."""
        direction = request.direction
        text = request.text

        if direction == TranslationDirection.GENZ_TO_ENGLISH:
            prompt = f"""You are a GenZ slang translator. Translate the following GenZ slang or internet language to clear, standard English.

Text to translate: "{text}"

Provide only the translated text in standard English. Do not include explanations or additional text.

Translation:"""
        else:
            prompt = f"""You are a GenZ slang translator. Translate the following standard English to GenZ slang or internet language.

Text to translate: "{text}"

Provide only the translated text in GenZ slang. Do not include explanations or additional text.

Translation:"""

        return prompt

    @tracer.trace_external_call("bedrock", "invoke")
    def _call_bedrock_api(self, prompt: str) -> BedrockResponse:
        """Call AWS Bedrock API."""
        try:
            request_body = {
                "prompt": prompt,
                "max_tokens": self.bedrock_config.get("max_tokens", 1000),
                "temperature": self.bedrock_config.get("temperature", 0.7),
                "top_p": self.bedrock_config.get("top_p", 0.9),
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_config["model_id"],
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())

            return BedrockResponse(
                completion=response_body.get("completion", ""),
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

        if completion.startswith("Translation:") or completion.startswith(
            "translation:"
        ):
            completion = completion.split(":", 1)[1].strip()

        if not completion:
            raise BusinessLogicError("Invalid response format from Bedrock")

        return completion

    def _calculate_confidence_score(self, response: BedrockResponse) -> Optional[float]:
        """Calculate confidence score based on response quality."""
        # Simple heuristic - in production, you might use more sophisticated analysis
        completion = response.completion.strip()

        if not completion:
            return 0.0

        # Basic confidence based on response length and content
        if len(completion) < 3:
            return 0.3
        elif len(completion) > 50:
            return 0.9
        else:
            return 0.7

    def _save_translation_history(self, response: Translation, user_id: str) -> None:
        """Save translation to history."""
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

    def get_translation_history(
        self,
        user_id: str,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get user's translation history."""
        result = self.translation_repository.get_user_translations(
            user_id, limit, last_evaluated_key
        )

        return {
            "translations": result.items,
            "total_count": result.count,
            "has_more": result.last_evaluated_key is not None,
            "last_evaluated_key": result.last_evaluated_key,
        }

    def delete_translation(self, user_id: str, translation_id: str) -> bool:
        """Delete a translation from history."""
        return self.translation_repository.delete_translation(user_id, translation_id)

    @tracer.trace_method("delete_user_translations")
    def delete_user_translations(self, user_id: str) -> int:
        """Delete all translations for a user. Returns number of deleted records."""
        try:
            # Get all user translations
            translations = self.translation_repository.get_user_translations(user_id, limit=1000)
            deleted_count = 0
            
            # Delete each translation
            for translation in translations.items:
                success = self.translation_repository.delete_translation(user_id, translation.translation_id)
                if success:
                    deleted_count += 1
            
            logger.log_business_event(
                "user_translations_deleted",
                {"user_id": user_id, "deleted_count": deleted_count}
            )
            
            return deleted_count
            
        except Exception as e:
            logger.log_error(e, {"operation": "delete_user_translations", "user_id": user_id})
            return 0
