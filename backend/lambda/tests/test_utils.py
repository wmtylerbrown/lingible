"""Tests for utility modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timezone

from src.utils.exceptions import (
    AppException,
    BusinessLogicError,
    ValidationError,
    AuthenticationError,
    InsufficientPermissionsError,
    SystemError,
    ErrorCode
)
from src.utils.response import create_model_response, create_error_response
from src.utils.envelopes import (
    TranslationEnvelope,
    SimpleAuthenticatedEnvelope,
    PathParameterEnvelope,
    TranslationHistoryEnvelope,
)
from src.utils.config import ConfigService
from src.utils.smart_logger import SmartLogger


class TestExceptions:
    """Test custom exception classes."""

    def test_app_exception_base(self):
        """Test base AppException."""
        exception = AppException("Test error", ErrorCode.INVALID_INPUT, 400)

        assert str(exception) == "Test error"
        assert exception.error_code == ErrorCode.INVALID_INPUT
        assert exception.status_code == 400

    def test_business_logic_error(self):
        """Test BusinessLogicError."""
        exception = BusinessLogicError("Business rule violation")

        assert str(exception) == "Business rule violation"
        assert exception.error_code == ErrorCode.USAGE_LIMIT_EXCEEDED.value
        assert exception.status_code == 400

    def test_validation_error(self):
        """Test ValidationError."""
        exception = ValidationError("Invalid input")

        assert str(exception) == "Invalid input"
        assert exception.error_code == ErrorCode.INVALID_INPUT.value
        assert exception.status_code == 422  # UNPROCESSABLE_ENTITY

    def test_authentication_error(self):
        """Test AuthenticationError."""
        exception = AuthenticationError("Invalid credentials")

        assert str(exception) == "Invalid credentials"
        assert exception.error_code == ErrorCode.INVALID_TOKEN.value
        assert exception.status_code == 401

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError."""
        exception = InsufficientPermissionsError("Insufficient permissions")

        assert str(exception) == "Insufficient permissions"
        assert exception.error_code == ErrorCode.INSUFFICIENT_PERMISSIONS.value
        assert exception.status_code == 403

    def test_system_error(self):
        """Test SystemError."""
        exception = SystemError("Internal server error")

        assert str(exception) == "Internal server error"
        assert exception.error_code == ErrorCode.DATABASE_ERROR.value  # Default error code
        assert exception.status_code == 500


class TestResponseUtils:
    """Test response utility functions."""

    def test_create_success_response(self):
        """Test creating success response with Pydantic model."""
        from src.models.quiz import QuizHistory

        history = QuizHistory(
            user_id="test_123",
            total_quizzes=1,
            average_score=85.0,
            best_score=100.0,
            total_correct=10,
            total_questions=10,
            accuracy_rate=1.0,
            quizzes_today=0,
            can_take_quiz=True,
        )

        response = create_model_response(history)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["user_id"] == "test_123"
        assert body["total_quizzes"] == 1

    def test_create_success_response_with_custom_status(self):
        """Test creating success response with custom status code."""
        from src.models.quiz import QuizHistory

        history = QuizHistory(
            user_id="test",
            total_quizzes=1,
            average_score=85.0,
            best_score=100.0,
            total_correct=10,
            total_questions=10,
            accuracy_rate=1.0,
            quizzes_today=0,
            can_take_quiz=True,
        )

        response = create_model_response(history, status_code=201)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["user_id"] == "test"

    def test_create_error_response(self):
        """Test creating error response."""
        error = BusinessLogicError("Test error")

        response = create_error_response(error)

        assert response["statusCode"] == 400
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["message"] == "Test error"
        assert body["error_code"] == "BIZ_001"
        assert "timestamp" in body
        assert isinstance(body["timestamp"], str)  # ISO8601 string

    def test_create_error_response_with_details(self):
        """Test creating error response with usage limit details."""
        from src.utils.exceptions import UsageLimitExceededError

        error = UsageLimitExceededError("quiz_questions", 10, 10)

        response = create_error_response(error)

        assert response["statusCode"] == 429
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["status_code"] == 429
        assert body["details"]["limit_type"] == "quiz_questions"
        assert body["details"]["current_usage"] == 10  # Should be int, not string
        assert body["details"]["limit"] == 10  # Should be int, not string
        assert isinstance(body["details"]["current_usage"], int)
        assert isinstance(body["details"]["limit"], int)

    def test_create_model_response_with_quiz_history(self):
        """Test create_model_response with QuizHistory model."""
        from src.models.quiz import QuizHistory

        history = QuizHistory(
            user_id="test_user",
            total_quizzes=10,
            average_score=85.5,
            best_score=100,
            total_correct=85,
            total_questions=100,
            accuracy_rate=0.85,
            quizzes_today=2,
            can_take_quiz=True,
            reason=None,
        )

        response = create_model_response(history)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        # Body should be a JSON string from to_json()
        assert isinstance(response["body"], str)
        body_dict = json.loads(response["body"])
        assert body_dict["user_id"] == "test_user"
        assert body_dict["total_quizzes"] == 10

    def test_create_model_response_with_quiz_result(self):
        """Test create_model_response with QuizResult model."""
        from src.models.quiz import QuizResult

        result = QuizResult(
            session_id="session_123",
            score=25,
            total_possible=20,
            correct_count=2,
            total_questions=2,
            time_taken_seconds=45,
            share_text="Test share text",
            share_url=None,
        )

        response = create_model_response(result)

        assert response["statusCode"] == 200
        body_dict = json.loads(response["body"])
        assert body_dict["session_id"] == "session_123"
        assert body_dict["score"] == 25
        assert body_dict["correct_count"] == 2


class TestEnvelopes:
    """Test envelope classes."""

    def test_authenticated_api_gateway_envelope(self):
        """Test AuthenticatedAPIGatewayEnvelope."""
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
            "body": '{"text": "Hello", "direction": "english_to_genz"}'
        }

        envelope = SimpleAuthenticatedEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.request_id == "req_123"

    def test_translation_envelope(self):
        """Test TranslationEnvelope."""
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
            "body": '{"text": "Hello world", "direction": "english_to_genz"}'
        }

        envelope = TranslationEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.request_body.text == "Hello world"
        assert parsed_event.request_body.direction.value == "english_to_genz"

    def test_translation_history_envelope(self):
        """Test TranslationHistoryEnvelope."""
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
            "queryStringParameters": {
                "limit": "10",
                "offset": "0"
            }
        }

        envelope = TranslationHistoryEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.limit == 10
        assert parsed_event.offset == 0

    def test_simple_authenticated_envelope(self):
        """Test SimpleAuthenticatedEnvelope."""
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
            }
        }

        envelope = SimpleAuthenticatedEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"

    def test_path_parameter_envelope(self):
        """Test PathParameterEnvelope."""
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
            "pathParameters": {
                "id": "trans_789"
            }
        }

        envelope = PathParameterEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.translation_id == "trans_789"

    def test_envelope_missing_authorizer(self):
        """Test envelope with missing authorizer raises error."""
        event = {
            "requestContext": {
                "requestId": "req_123"
            }
        }

        envelope = SimpleAuthenticatedEnvelope()

        with pytest.raises(AuthenticationError):
            envelope.parse(event)

    def test_envelope_missing_user_id(self):
        """Test envelope with missing user_id raises error."""
        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "email": "test@example.com",
                        "aud": "test_client",
                        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
                        "exp": 1234567890,
                        "iat": 1234567890,
                        "jti": "test_jti"
                        # Missing required 'sub' field
                    }
                },
                "requestId": "req_123"
            }
        }

        envelope = SimpleAuthenticatedEnvelope()

        with pytest.raises(AuthenticationError):
            envelope.parse(event)


class TestConfig:
    """Test configuration management."""

    @patch.dict('os.environ', {
        'ENVIRONMENT': 'test',
        'APP_NAME': 'lingible-test',
        'AWS_REGION': 'us-east-1'
    })
    def test_config_initialization(self):
        """Test AppConfig initialization with environment variables."""
        config = ConfigService()

        assert config.environment == "test"
        assert config.app_name == "lingible-test"
        assert config.aws_region == "us-east-1"

    @patch.dict('os.environ', {}, clear=True)
    def test_config_defaults(self):
        """Test AppConfig initialization with defaults."""
        config = ConfigService()

        assert config.environment == "development"
        assert config.app_name == "lingible-backend"

    def test_config_bedrock_config(self):
        """Test Bedrock configuration."""
        config = ConfigService()

        assert "model_id" in config.bedrock_config
        assert "max_tokens" in config.bedrock_config
        assert "temperature" in config.bedrock_config

    def test_config_apple_store_config(self):
        """Test Apple Store configuration."""
        config = ConfigService()

        assert config.apple_store["bundle_id"] == "com.lingible.lingible"
        assert "sandbox_url" in config.apple_store
        assert "production_url" in config.apple_store

    def test_config_google_play_config(self):
        """Test Google Play configuration."""
        config = ConfigService()

        assert config.google_play["package_name"] == "com.lingible.lingible"
        assert "api_timeout" in config.google_play


class TestSmartLogger:
    """Test SmartLogger."""

    def test_logger_initialization(self):
        """Test SmartLogger initialization."""
        logger = SmartLogger("test-service")

        assert logger.service_name == "test-service"

    @patch('src.utils.smart_logger.Logger')
    def test_log_business_event(self, mock_logger):
        """Test logging business events."""
        logger = SmartLogger("test-service")

        logger.log_business_event("user_created", {"user_id": "test_123"})

        mock_logger.return_value.info.assert_called_once()

    @patch('src.utils.smart_logger.Logger')
    def test_log_error(self, mock_logger):
        """Test logging errors."""
        logger = SmartLogger("test-service")
        error = Exception("Test error")

        logger.log_error(error, {"operation": "test"})

        mock_logger.return_value.error.assert_called_once()

    @patch('src.utils.smart_logger.Logger')
    def test_log_request(self, mock_logger):
        """Test logging requests."""
        logger = SmartLogger("test-service")

        logger.log_request(
            {
                "httpMethod": "POST",
                "path": "/translate",
                "headers": {},
                "queryStringParameters": {"user_id": "test_123"},
            }
        )

        mock_logger.return_value.info.assert_called_once()

    @patch('src.utils.smart_logger.Logger')
    def test_log_response(self, mock_logger):
        """Test logging responses."""
        logger = SmartLogger("test-service")

        logger.log_response(
            {"statusCode": 200, "body": json.dumps({"success": True})}, 15.0
        )

        mock_logger.return_value.info.assert_called_once()


class TestErrorCodes:
    """Test error code enum."""

    def test_error_code_values(self):
        """Test ErrorCode enum values."""
        assert ErrorCode.VALIDATION_ERROR.value == "VAL_001"
        assert ErrorCode.BUSINESS_LOGIC_ERROR.value == "BIZ_003"
        assert ErrorCode.AUTHENTICATION_ERROR.value == "AUTH_001"
        assert ErrorCode.AUTHORIZATION_ERROR.value == "AUTH_003"
        assert ErrorCode.SYSTEM_ERROR.value == "SYS_003"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_001"
        assert ErrorCode.USAGE_LIMIT_EXCEEDED.value == "BIZ_001"
        assert ErrorCode.SUBSCRIPTION_REQUIRED.value == "BIZ_004"
