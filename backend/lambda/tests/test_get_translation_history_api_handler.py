"""Tests for get translation history API handler."""

import json
import importlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from unittest.mock import Mock, patch

from models.translations import (
    TranslationDirection,
    TranslationHistory,
    TranslationHistoryServiceResult,
)
from utils.exceptions import InsufficientPermissionsError


class TestTranslationHistoryAPIHandler:
    """Test translation history API handler."""

    @pytest.fixture
    def module(self):
        return importlib.import_module("handlers.get_translation_history_api.handler")

    @pytest.fixture
    def handler(self, module):
        return module.handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_query_params):
        """Sample API Gateway event for translation history."""
        event = api_gateway_event_with_query_params.copy()
        event["resource"] = "/translations/history"
        event["path"] = "/translations/history"
        event["httpMethod"] = "GET"
        event["queryStringParameters"] = {"limit": "10", "offset": "0"}
        event["multiValueQueryStringParameters"] = {"limit": ["10"], "offset": ["0"]}
        event["requestContext"]["authorizer"]["claims"]["sub"] = "premium_user_456"
        event["requestContext"]["authorizer"]["claims"]["email"] = "premium@example.com"
        return event

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
