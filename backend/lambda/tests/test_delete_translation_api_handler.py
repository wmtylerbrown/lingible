"""Tests for delete translation API handler."""

import json
import importlib

import pytest
from unittest.mock import Mock, patch

from utils.exceptions import BusinessLogicError


class TestDeleteTranslationHandler:
    """Test delete translation handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.delete_translation_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_path_params):
        """Sample API Gateway event for deleting translation."""
        event = api_gateway_event_with_path_params.copy()
        event["pathParameters"]["translation_id"] = "trans_789"
        event["resource"] = "/translations/{translation_id}"
        event["path"] = "/translations/trans_789"
        event["httpMethod"] = "DELETE"
        event["requestContext"]["authorizer"]["claims"]["sub"] = "premium_user_456"
        event["requestContext"]["authorizer"]["claims"]["email"] = "premium@example.com"
        return event

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
