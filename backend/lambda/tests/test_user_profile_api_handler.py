"""Tests for user profile API handler."""

import json
import importlib
from datetime import datetime, timezone

import pytest
from unittest.mock import Mock, patch

from models.users import UserTier, UserStatus, UserResponse


class TestUserProfileAPIHandler:
    """Test user profile API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.user_profile_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, authenticated_api_gateway_event):
        """Sample API Gateway event for user profile."""
        event = authenticated_api_gateway_event.copy()
        event["resource"] = "/user/profile"
        event["path"] = "/user/profile"
        event["httpMethod"] = "GET"
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["requestContext"]["authorizer"]["claims"]["email"] = "test@example.com"
        return event

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
        assert body["tier"] == "free"  # Enum value, not enum name

    def test_get_user_profile_not_found(self, module, handler, sample_event, mock_config):
        """Test user profile retrieval when user doesn't exist."""
        with patch(f"{module.__name__}.user_service") as mock_service:
            mock_service.get_user.return_value = None

            response = handler(sample_event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["status_code"] == 404
