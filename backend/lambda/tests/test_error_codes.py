"""Tests for error code enum."""

import pytest

from utils.exceptions import ErrorCode


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
