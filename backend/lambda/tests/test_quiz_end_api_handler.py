"""Tests for quiz end API handler."""

import os
import pytest
from unittest.mock import Mock, patch
import json

from models.quiz import QuizEndRequest, QuizResult


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


class TestQuizEndAPIHandler:
    """Test POST /quiz/end handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from handlers.quiz_end_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_body):
        """Sample API Gateway event for quiz end."""
        end_request = QuizEndRequest(session_id="session_123")

        event = api_gateway_event_with_body.copy()
        event["resource"] = "/quiz/end"
        event["path"] = "/quiz/end"
        event["httpMethod"] = "POST"
        event["body"] = json.dumps(end_request.model_dump())
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        return event

    def test_end_session_success(self, handler, sample_event, mock_config):
        """Test successful session end."""
        with patch(
            "handlers.quiz_end_api.handler.quiz_service"
        ) as mock_service:
            mock_result = QuizResult(
                session_id="session_123",
                score=35.5,
                total_possible=50.0,
                correct_count=4,
                total_questions=5,
                time_taken_seconds=300.0,
                share_text="Test share text",
            )
            mock_service.end_session.return_value = mock_result

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["session_id"] == "session_123"
            assert body_dict["score"] == 35.5
            assert body_dict["correct_count"] == 4
            assert body_dict["total_questions"] == 5
