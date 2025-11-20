"""Tests for delete all translations API handler."""

import json
import importlib

import pytest
from unittest.mock import Mock, patch

from utils.exceptions import InsufficientPermissionsError


class TestDeleteAllTranslationsHandler:
    """Test delete all translations handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.delete_translations_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, authenticated_api_gateway_event):
        """Sample API Gateway event for deleting all translations."""
        event = authenticated_api_gateway_event.copy()
        event["resource"] = "/translations"
        event["path"] = "/translations"
        event["httpMethod"] = "DELETE"
        event["requestContext"]["authorizer"]["claims"]["sub"] = "premium_user_456"
        event["requestContext"]["authorizer"]["claims"]["email"] = "premium@example.com"
        return event

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
