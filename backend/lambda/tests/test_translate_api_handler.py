"""Tests for translate API handler."""

import json
import importlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError as PydanticValidationError

from models.translations import (
    TranslationDirection,
    Translation,
)
from models.users import UserTier
from utils.exceptions import BusinessLogicError


class TestTranslateAPIHandler:
    """Test translate API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.translate_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_body):
        """Sample API Gateway event for translation."""
        event = api_gateway_event_with_body.copy()
        event["resource"] = "/translate"
        event["path"] = "/translate"
        event["httpMethod"] = "POST"
        event["body"] = '{"text": "Hello world", "direction": "english_to_genz"}'
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["requestContext"]["authorizer"]["claims"]["email"] = "test@example.com"
        return event

    def test_successful_translation(self, module, handler, sample_event, mock_config):
        """Test successful translation request."""
        translation = Translation(
            original_text="Hello world",
            translated_text="Hola mundo",
            direction=TranslationDirection.ENGLISH_TO_GENZ,
            confidence_score=Decimal("0.95"),
            translation_id="trans_789",
            created_at=datetime.now(timezone.utc),
            processing_time_ms=120,
            model_used="bedrock",
            translation_failed=False,
            failure_reason=None,
            user_message=None,
            can_submit_feedback=True,
            daily_used=5,
            daily_limit=10,
            tier=UserTier.FREE,
        )

        mock_service = Mock()
        mock_service.translate_text.return_value = translation

        with patch(f"{module.__name__}.translation_service", mock_service):
            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["translation_id"] == "trans_789"
        assert body["translated_text"] == "Hola mundo"
        assert body["tier"] == "free"  # Enum value, not enum name

    def test_translation_with_empty_text(self, handler, mock_config):
        """Test translation with empty text."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "test_user_123",
                        "email": "test@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti",
                    }
                },
                "requestId": "req_123",
            },
            "body": '{"text": "", "direction": "english_to_genz"}',
        }

        with pytest.raises(PydanticValidationError):
            handler(event, {})

    def test_translation_usage_limit_exceeded(
        self, module, handler, sample_event, mock_config
    ):
        """Test translation when usage limit is exceeded."""
        mock_service = Mock()
        mock_service.translate_text.side_effect = BusinessLogicError(
            "Daily usage limit exceeded"
        )

        with patch(f"{module.__name__}.translation_service", mock_service):
            response = handler(sample_event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "Daily usage limit exceeded" in body["message"]
