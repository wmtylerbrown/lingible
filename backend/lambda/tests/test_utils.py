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
from src.utils.response import create_success_response, create_error_response
from src.utils.envelopes import (
    AuthenticatedAPIGatewayEnvelope,
    TranslationEnvelope,
    SimpleAuthenticatedEnvelope,
    PathParameterEnvelope
)
from src.utils.config import ConfigService
from src.utils.logging import SmartLogger


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
        assert exception.error_code == ErrorCode.BUSINESS_LOGIC_ERROR
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
        """Test creating success response."""
        data = {"message": "Success", "user_id": "test_123"}

        response = create_success_response(data)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert json.loads(response["body"])["success"] is True
        assert json.loads(response["body"])["data"]["message"] == "Success"

    def test_create_success_response_with_custom_status(self):
        """Test creating success response with custom status code."""
        data = {"created": True}

        response = create_success_response(data, status_code=201)

        assert response["statusCode"] == 201
        assert json.loads(response["body"])["success"] is True

    def test_create_error_response(self):
        """Test creating error response."""
        error = BusinessLogicError("Test error")

        response = create_error_response(error)

        assert response["statusCode"] == 400
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["error"]["message"] == "Test error"
        assert body["error"]["code"] == "BUSINESS_LOGIC_ERROR"

    def test_create_error_response_with_custom_status(self):
        """Test creating error response with custom status code."""
        error = SystemError("Internal error")

        response = create_error_response(error, status_code=503)

        assert response["statusCode"] == 503


class TestEnvelopes:
    """Test envelope classes."""

    def test_authenticated_api_gateway_envelope(self):
        """Test AuthenticatedAPIGatewayEnvelope."""
        event = {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                    "username": "testuser"
                },
                "requestId": "req_123"
            },
            "body": '{"text": "Hello", "direction": "english_to_genz"}'
        }

        envelope = AuthenticatedAPIGatewayEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.username == "testuser"
        assert parsed_event.request_id == "req_123"

    def test_translation_envelope(self):
        """Test TranslationEnvelope."""
        event = {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                    "username": "testuser"
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
                    "user_id": "test_user_123",
                    "username": "testuser"
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
                    "user_id": "test_user_123",
                    "username": "testuser"
                },
                "requestId": "req_123"
            }
        }

        envelope = SimpleAuthenticatedEnvelope()
        parsed_event = envelope.parse(event)

        assert parsed_event.user_id == "test_user_123"
        assert parsed_event.username == "testuser"

    def test_path_parameter_envelope(self):
        """Test PathParameterEnvelope."""
        event = {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                    "username": "testuser"
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

        envelope = AuthenticatedAPIGatewayEnvelope()

        with pytest.raises(ValueError):
            envelope.parse(event)

    def test_envelope_missing_user_id(self):
        """Test envelope with missing user_id raises error."""
        event = {
            "requestContext": {
                "authorizer": {
                    "username": "testuser"
                },
                "requestId": "req_123"
            }
        }

        envelope = AuthenticatedAPIGatewayEnvelope()

        with pytest.raises(ValueError):
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

    @patch('src.utils.logging.logger')
    def test_log_business_event(self, mock_logger):
        """Test logging business events."""
        logger = SmartLogger("test-service")

        logger.log_business_event("user_created", {"user_id": "test_123"})

        mock_logger.info.assert_called_once()

    @patch('src.utils.logging.logger')
    def test_log_error(self, mock_logger):
        """Test logging errors."""
        logger = SmartLogger("test-service")
        error = Exception("Test error")

        logger.log_error(error, {"operation": "test"})

        mock_logger.error.assert_called_once()

    @patch('src.utils.logging.logger')
    def test_log_request(self, mock_logger):
        """Test logging requests."""
        logger = SmartLogger("test-service")

        logger.log_request("POST", "/translate", {"user_id": "test_123"})

        mock_logger.info.assert_called_once()

    @patch('src.utils.logging.logger')
    def test_log_response(self, mock_logger):
        """Test logging responses."""
        logger = SmartLogger("test-service")

        logger.log_response(200, {"success": True})

        mock_logger.info.assert_called_once()


class TestErrorCodes:
    """Test error code enum."""

    def test_error_code_values(self):
        """Test ErrorCode enum values."""
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.BUSINESS_LOGIC_ERROR.value == "BUSINESS_LOGIC_ERROR"
        assert ErrorCode.AUTHENTICATION_ERROR.value == "AUTHENTICATION_ERROR"
        assert ErrorCode.AUTHORIZATION_ERROR.value == "AUTHORIZATION_ERROR"
        assert ErrorCode.SYSTEM_ERROR.value == "SYSTEM_ERROR"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_LIMIT_EXCEEDED"
        assert ErrorCode.USAGE_LIMIT_EXCEEDED.value == "USAGE_LIMIT_EXCEEDED"
        assert ErrorCode.SUBSCRIPTION_REQUIRED.value == "SUBSCRIPTION_REQUIRED"
