"""Tests for user usage API handler."""

import json
import importlib
from datetime import datetime, timezone

import pytest
from unittest.mock import Mock, patch

from models.users import UserTier, UserUsageResponse


class TestUserUsageAPIHandler:
    """Test user usage API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.user_usage_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, authenticated_api_gateway_event):
        """Sample API Gateway event for user usage."""
        event = authenticated_api_gateway_event.copy()
        event["resource"] = "/user/usage"
        event["path"] = "/user/usage"
        event["httpMethod"] = "GET"
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        event["requestContext"]["authorizer"]["claims"]["email"] = "test@example.com"
        return event

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
