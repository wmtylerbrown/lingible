"""Tests for Lambda handlers."""

import json
import importlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError as PydanticValidationError

from src.models.translations import (
    TranslationDirection,
    Translation,
    TranslationHistory,
    TranslationHistoryServiceResult,
)
from src.models.users import UserTier, UserStatus, UserResponse, UserUsageResponse
from src.utils.exceptions import BusinessLogicError, InsufficientPermissionsError


class TestTranslateAPIHandler:
    """Test translate API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.translate_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for translation."""
        return {
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
            "body": '{"text": "Hello world", "direction": "english_to_genz"}',
        }

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
        assert body["tier"] == str(UserTier.FREE)

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


class TestUserProfileAPIHandler:
    """Test user profile API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.user_profile_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for user profile."""
        return {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "test_user_123",
                        "email": "test@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            }
        }

    def test_get_user_profile_success(self, module, handler, sample_event, mock_config):
        """Test successful user profile retrieval."""
        with patch(f"{module.__name__}.user_service") as mock_service:
            mock_user = Mock()
            mock_user.to_api_response.return_value = UserResponse(
                user_id="test_user_123",
                email="test@example.com",
                username="testuser",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                slang_submitted_count=0,
                slang_approved_count=0,
            )
            mock_service.get_user.return_value = mock_user

            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "test_user_123"
        assert body["tier"] == str(UserTier.FREE)

    def test_get_user_profile_not_found(self, module, handler, sample_event, mock_config):
        """Test user profile retrieval when user doesn't exist."""
        with patch(f"{module.__name__}.user_service") as mock_service:
            mock_service.get_user.return_value = None

            response = handler(sample_event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["status_code"] == 404


class TestUserUsageAPIHandler:
    """Test user usage API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.user_usage_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for user usage."""
        return {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "test_user_123",
                        "email": "test@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            }
        }

    def test_get_user_usage_success(self, module, handler, sample_event, mock_config):
        """Test successful user usage retrieval."""
        usage_response = UserUsageResponse(
            tier=UserTier.FREE,
            daily_limit=10,
            daily_used=5,
            daily_remaining=5,
            reset_date=datetime.now(timezone.utc),
            current_max_text_length=280,
            free_tier_max_length=280,
            premium_tier_max_length=1000,
            free_daily_limit=10,
            premium_daily_limit=100,
        )

        with patch(f"{module.__name__}.user_service") as mock_service:
            mock_service.get_user_usage.return_value = usage_response

            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["daily_used"] == 5
        assert body["daily_limit"] == 10


class TestTranslationHistoryAPIHandler:
    """Test translation history API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.get_translation_history.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for translation history."""
        return {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "premium_user_456",
                        "email": "premium@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            },
            "queryStringParameters": {
                "limit": "10",
                "offset": "0"
            }
        }

    def test_get_translation_history_success(
        self, module, handler, sample_event, mock_config
    ):
        """Test successful translation history retrieval."""
        history_items = [
            TranslationHistory(
                translation_id="trans_1",
                user_id="premium_user_456",
                original_text="Hello",
                translated_text="Hola",
                direction=TranslationDirection.ENGLISH_TO_GENZ,
                confidence_score=Decimal("0.95"),
                created_at=datetime.now(timezone.utc),
                model_used="bedrock",
            )
        ]
        result = TranslationHistoryServiceResult(
            translations=history_items,
            total_count=1,
            has_more=False,
            last_evaluated_key=None,
        )

        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.get_translation_history.return_value = result

            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["translations"]) == 1
        assert body["translations"][0]["translation_id"] == "trans_1"

    def test_get_translation_history_free_user(
        self, module, handler, sample_event, mock_config
    ):
        """Test translation history retrieval for free user (should fail)."""
        # Change user_id to indicate free user
        sample_event["requestContext"]["authorizer"]["claims"]["sub"] = "free_user_123"

        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.get_translation_history.side_effect = InsufficientPermissionsError(
                "Premium subscription required"
            )

            response = handler(sample_event, {})

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "Premium subscription required" in body["message"]


class TestHealthAPIHandler:
    """Test health API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.health_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    def test_health_check_success(self, handler):
        """Test successful health check."""
        event = {}
        context = {}

        response = handler(event, context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
        assert "version" in body
        assert "timestamp" in body


class TestDeleteTranslationHandler:
    """Test delete translation handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.delete_translation.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for deleting translation."""
        return {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "premium_user_456",
                        "email": "premium@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            },
            "pathParameters": {
                "translation_id": "trans_789"
            }
        }

    def test_delete_translation_success(
        self, module, handler, sample_event, mock_config
    ):
        """Test successful translation deletion."""
        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.delete_translation.return_value = True

            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["data"]["translation_id"] == "trans_789"

    def test_delete_translation_not_found(
        self, module, handler, sample_event, mock_config
    ):
        """Test deleting translation that doesn't exist."""
        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.delete_translation.return_value = False

            response = handler(sample_event, {})

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "unexpected" in body["message"].lower()

    def test_delete_translation_unauthorized(
        self, module, handler, sample_event, mock_config
    ):
        """Test deleting translation without proper authorization."""
        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.delete_translation.side_effect = BusinessLogicError(
                "Not authorized to delete this translation"
            )

            response = handler(sample_event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "Not authorized" in body["message"]


class TestDeleteAllTranslationsHandler:
    """Test delete all translations handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("src.handlers.delete_translations.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for deleting all translations."""
        return {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "premium_user_456",
                        "email": "premium@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            }
        }

    def test_delete_all_translations_success(
        self, module, handler, sample_event, mock_config
    ):
        """Test successful deletion of all translations."""
        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.delete_user_translations.return_value = 3

            response = handler(sample_event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["data"]["deleted_count"] == 3

    def test_delete_all_translations_free_user(
        self, module, handler, sample_event, mock_config
    ):
        """Test deleting all translations for free user (should fail)."""
        # Change user_id to indicate free user
        sample_event["requestContext"]["authorizer"]["claims"]["sub"] = "free_user_123"

        with patch(f"{module.__name__}.translation_service") as mock_service:
            mock_service.delete_user_translations.side_effect = InsufficientPermissionsError(
                "Premium subscription required"
            )

            response = handler(sample_event, {})

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "Premium subscription required" in body["message"]
