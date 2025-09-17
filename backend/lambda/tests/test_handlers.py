"""Tests for Lambda handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.models.translations import TranslationDirection
from src.models.users import UserTier, UserStatus
from src.models.events import TranslationEvent, SimpleAuthenticatedEvent, PathParameterEvent
from src.utils.exceptions import BusinessLogicError, ValidationError


class TestTranslateAPIHandler:
    """Test translate API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.translate_api.translate_api_handler import handler
        return handler

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
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            },
            "body": '{"text": "Hello world", "direction": "english_to_genz"}'
        }

    def test_successful_translation(self, handler, sample_event, mock_config):
        """Test successful translation request."""
        with patch('src.handlers.translate_api.translate_api_handler.TranslationService') as mock_service_class, \
             patch('src.handlers.translate_api.translate_api_handler.UserService') as mock_user_service_class:

            # Mock services
            mock_service = Mock()
            mock_service.translate.return_value = Mock(
                translation_id="trans_789",
                original_text="Hello world",
                translated_text="Hola mundo",
                direction=TranslationDirection.ENGLISH_TO_GENZ,
                confidence_score=0.95
            )
            mock_service_class.return_value = mock_service

            mock_user_service = Mock()
            mock_user_service.get_user_profile.return_value = Mock(
                user_id="test_user_123",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE
            )
            mock_user_service_class.return_value = mock_user_service

            # Call handler
            response = handler(sample_event, {})

            # Verify response
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert body["data"]["translation_id"] == "trans_789"
            assert body["data"]["translated_text"] == "Hola mundo"

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
                        "jti": "test_jti"
                    }
                },
                "requestId": "req_123"
            },
            "body": '{"text": "", "direction": "english_to_genz"}'
        }

        with patch('src.handlers.translate_api.translate_api_handler.TranslationService') as mock_service_class, \
             patch('src.handlers.translate_api.translate_api_handler.UserService') as mock_user_service_class:

            mock_service = Mock()
            mock_service.translate.side_effect = ValidationError("Text cannot be empty")
            mock_service_class.return_value = mock_service

            mock_user_service = Mock()
            mock_user_service.get_user_profile.return_value = Mock(
                user_id="test_user_123",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE
            )
            mock_user_service_class.return_value = mock_user_service

            response = handler(event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Text cannot be empty" in body["error"]["message"]

    def test_translation_usage_limit_exceeded(self, handler, sample_event, mock_config):
        """Test translation when usage limit is exceeded."""
        with patch('src.handlers.translate_api.translate_api_handler.TranslationService') as mock_service_class, \
             patch('src.handlers.translate_api.translate_api_handler.UserService') as mock_user_service_class:

            mock_service = Mock()
            mock_service.translate.side_effect = BusinessLogicError("Daily usage limit exceeded")
            mock_service_class.return_value = mock_service

            mock_user_service = Mock()
            mock_user_service.get_user_profile.return_value = Mock(
                user_id="test_user_123",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE
            )
            mock_user_service_class.return_value = mock_user_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Daily usage limit exceeded" in body["error"]["message"]


class TestUserProfileAPIHandler:
    """Test user profile API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.user_profile_api.user_profile_api_handler import handler
        return handler

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

    def test_get_user_profile_success(self, handler, sample_event, mock_config):
        """Test successful user profile retrieval."""
        with patch('src.handlers.user_profile_api.user_profile_api_handler.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_user_profile.return_value = Mock(
                user_id="test_user_123",
                email="test@example.com",
                username="testuser",
                tier=UserTier.FREE,
                status=UserStatus.ACTIVE
            )
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert body["data"]["user_id"] == "test_user_123"
            assert body["data"]["email"] == "test@example.com"

    def test_get_user_profile_not_found(self, handler, sample_event, mock_config):
        """Test user profile retrieval when user doesn't exist."""
        with patch('src.handlers.user_profile_api.user_profile_api_handler.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_user_profile.return_value = None
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 404
            body = json.loads(response["body"])
            assert body["success"] is False


class TestUserUsageAPIHandler:
    """Test user usage API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.user_usage_api.user_usage_api_handler import handler
        return handler

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

    def test_get_user_usage_success(self, handler, sample_event, mock_config):
        """Test successful user usage retrieval."""
        with patch('src.handlers.user_usage_api.user_usage_api_handler.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_user_usage.return_value = {
                "user_id": "test_user_123",
                "daily_used": 5,
                "daily_limit": 10,
                "tier": "free"
            }
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert body["data"]["daily_used"] == 5
            assert body["data"]["daily_limit"] == 10


class TestTranslationHistoryAPIHandler:
    """Test translation history API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.translation_history_api.get_translation_history import handler
        return handler

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

    def test_get_translation_history_success(self, handler, sample_event, mock_config):
        """Test successful translation history retrieval."""
        with patch('src.handlers.translation_history_api.get_translation_history.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_user_translations.return_value = [
                Mock(
                    translation_id="trans_1",
                    original_text="Hello",
                    translated_text="Hola",
                    direction=TranslationDirection.ENGLISH_TO_GENZ,
                    created_at="2024-01-01T00:00:00Z"
                ),
                Mock(
                    translation_id="trans_2",
                    original_text="World",
                    translated_text="Mundo",
                    direction=TranslationDirection.ENGLISH_TO_GENZ,
                    created_at="2024-01-01T00:00:00Z"
                )
            ]
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert len(body["data"]["translations"]) == 2
            assert body["data"]["translations"][0]["translation_id"] == "trans_1"

    def test_get_translation_history_free_user(self, handler, sample_event, mock_config):
        """Test translation history retrieval for free user (should fail)."""
        # Change user_id to indicate free user
        sample_event["requestContext"]["authorizer"]["claims"]["sub"] = "free_user_123"

        with patch('src.handlers.translation_history_api.get_translation_history.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_user_translations.side_effect = BusinessLogicError("Premium subscription required")
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Premium subscription required" in body["error"]["message"]


class TestHealthAPIHandler:
    """Test health API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.health_api.health_api_handler import handler
        return handler

    def test_health_check_success(self, handler):
        """Test successful health check."""
        event = {}
        context = {}

        response = handler(event, context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["data"]["service"] == "lingible-api"
        assert body["data"]["status"] == "healthy"
        assert "timestamp" in body["data"]


class TestDeleteTranslationHandler:
    """Test delete translation handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.translation_history_api.delete_translation import handler
        return handler

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
                "id": "trans_789"
            }
        }

    def test_delete_translation_success(self, handler, sample_event, mock_config):
        """Test successful translation deletion."""
        with patch('src.handlers.translation_history_api.delete_translation.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.delete_translation.return_value = True
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert body["data"]["deleted"] is True

    def test_delete_translation_not_found(self, handler, sample_event, mock_config):
        """Test deleting translation that doesn't exist."""
        with patch('src.handlers.translation_history_api.delete_translation.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.delete_translation.return_value = False
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 404
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Translation not found" in body["error"]["message"]

    def test_delete_translation_unauthorized(self, handler, sample_event, mock_config):
        """Test deleting translation without proper authorization."""
        with patch('src.handlers.translation_history_api.delete_translation.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.delete_translation.side_effect = BusinessLogicError("Not authorized to delete this translation")
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 403
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Not authorized" in body["error"]["message"]


class TestDeleteAllTranslationsHandler:
    """Test delete all translations handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.translation_history_api.delete_all_translations import handler
        return handler

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

    def test_delete_all_translations_success(self, handler, sample_event, mock_config):
        """Test successful deletion of all translations."""
        with patch('src.handlers.translation_history_api.delete_all_translations.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.delete_user_translations.return_value = True
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["success"] is True
            assert body["data"]["deleted"] is True

    def test_delete_all_translations_free_user(self, handler, sample_event, mock_config):
        """Test deleting all translations for free user (should fail)."""
        # Change user_id to indicate free user
        sample_event["requestContext"]["authorizer"]["claims"]["sub"] = "free_user_123"

        with patch('src.handlers.translation_history_api.delete_all_translations.TranslationService') as mock_service_class:
            mock_service = Mock()
            mock_service.delete_user_translations.side_effect = BusinessLogicError("Premium subscription required")
            mock_service_class.return_value = mock_service

            response = handler(sample_event, {})

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert body["success"] is False
            assert "Premium subscription required" in body["error"]["message"]
