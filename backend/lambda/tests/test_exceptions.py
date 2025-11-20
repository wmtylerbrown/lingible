"""Tests for exception classes."""

import pytest

from utils.exceptions import (
    AppException,
    BusinessLogicError,
    ValidationError,
    AuthenticationError,
    InsufficientPermissionsError,
    SystemError,
    ErrorCode
)


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
