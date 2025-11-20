"""Tests for quiz history API handler."""

import os
import pytest
from unittest.mock import Mock, patch
import json

from models.quiz import QuizHistory
from utils.exceptions import ValidationError, InsufficientPermissionsError


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


class TestQuizHistoryAPIHandler:
    """Test quiz history API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from handlers.quiz_history_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self, authenticated_api_gateway_event):
        """Sample API Gateway event for quiz history."""
        event = authenticated_api_gateway_event.copy()
        event["resource"] = "/quiz/history"
        event["path"] = "/quiz/history"
        event["httpMethod"] = "GET"
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        return event

    def test_get_quiz_history_success_premium(self, handler, sample_event, mock_config):
        """Test successful quiz history retrieval for premium user."""
        with patch(
            "handlers.quiz_history_api.handler.quiz_service"
        ) as mock_service:
            # Mock service response
            mock_history = QuizHistory(
                user_id="test_user_123",
                total_quizzes=10,
                average_score=85.5,
                best_score=100,
                total_correct=85,
                total_questions=100,
                accuracy_rate=0.85,
                quizzes_today=2,
                can_take_quiz=True,
                reason=None,
            )
            mock_service.check_quiz_eligibility.return_value = mock_history

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["user_id"] == "test_user_123"
            assert body_dict["total_quizzes"] == 10
            assert body_dict["average_score"] == 85.5
            assert body_dict["can_take_quiz"] is True

    def test_get_quiz_history_free_at_limit(self, handler, sample_event, mock_config):
        """Test quiz history for free user at daily limit."""
        with patch(
            "handlers.quiz_history_api.handler.quiz_service"
        ) as mock_service:
            mock_history = QuizHistory(
                user_id="test_user_123",
                total_quizzes=5,
                average_score=75.0,
                best_score=90,
                total_correct=38,
                total_questions=50,
                accuracy_rate=0.76,
                quizzes_today=3,
                can_take_quiz=False,
                reason="Daily limit reached. Upgrade to premium for unlimited quizzes!",
            )
            mock_service.check_quiz_eligibility.return_value = mock_history

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["can_take_quiz"] is False
            assert "limit" in body_dict["reason"].lower()

    def test_get_quiz_history_service_exception(self, handler, sample_event, mock_config):
        """Test handler handles service exceptions."""
        with patch(
            "handlers.quiz_history_api.handler.quiz_service"
        ) as mock_service:
            mock_service.check_quiz_eligibility.side_effect = Exception("Database error")

            response = handler(sample_event, {})

            assert response["statusCode"] == 500
            body_dict = json.loads(response["body"])
            assert body_dict["success"] is False
            assert "error" in body_dict or "message" in body_dict
