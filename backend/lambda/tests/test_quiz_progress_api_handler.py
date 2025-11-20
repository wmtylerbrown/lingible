"""Tests for quiz progress API handler."""

import os
import pytest
from unittest.mock import Mock, patch
import json

from models.quiz import QuizSessionProgress


@pytest.fixture(scope="module", autouse=True)
def ensure_quiz_env():
    """Ensure quiz environment variables are set before handlers are imported."""
    os.environ.setdefault("QUIZ_FREE_DAILY_LIMIT", "3")
    os.environ.setdefault("QUIZ_PREMIUM_UNLIMITED", "false")
    os.environ.setdefault("QUIZ_QUESTIONS_PER_QUIZ", "10")
    os.environ.setdefault("QUIZ_TIME_LIMIT_SECONDS", "60")
    os.environ.setdefault("QUIZ_POINTS_PER_CORRECT", "10")
    os.environ.setdefault("QUIZ_ENABLE_TIME_BONUS", "true")
    yield
    # Cleanup not needed - environment persists


class TestQuizProgressAPIHandler:
    """Test GET /quiz/progress handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from handlers.quiz_progress_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_query_params):
        """Sample API Gateway event for quiz progress."""
        event = api_gateway_event_with_query_params.copy()
        event["resource"] = "/quiz/progress"
        event["path"] = "/quiz/progress"
        event["httpMethod"] = "GET"
        event["queryStringParameters"] = {"session_id": "session_123"}
        event["multiValueQueryStringParameters"] = {"session_id": ["session_123"]}
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        return event

    def test_get_progress_success(self, handler, sample_event, mock_config):
        """Test successful progress retrieval."""
        with patch(
            "handlers.quiz_progress_api.handler.quiz_service"
        ) as mock_service:
            mock_progress = QuizSessionProgress(
                questions_answered=5,
                correct_count=4,
                total_score=35.5,
                accuracy=0.8,
                time_spent_seconds=300.0,
            )
            mock_service.get_session_progress.return_value = mock_progress

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["questions_answered"] == 5
            assert body_dict["correct_count"] == 4
            assert body_dict["total_score"] == 35.5
            assert body_dict["accuracy"] == 0.8

    def test_get_progress_missing_session_id(self, handler, mock_config, api_gateway_event_with_query_params):
        """Test progress retrieval without session_id."""
        event = api_gateway_event_with_query_params.copy()
        event["resource"] = "/quiz/progress"
        event["path"] = "/quiz/progress"
        event["httpMethod"] = "GET"
        event["queryStringParameters"] = None  # No session_id
        event["multiValueQueryStringParameters"] = None
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"

        response = handler(event, {})

        # Should return validation error
        assert response["statusCode"] == 422
