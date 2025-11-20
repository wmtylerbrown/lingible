"""Tests for quiz answer API handler."""

import pytest
from unittest.mock import Mock, patch
import json

from models.quiz import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizSessionProgress,
)


class TestQuizAnswerAPIHandler:
    """Test POST /quiz/answer handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from handlers.quiz_answer_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_body):
        """Sample API Gateway event for quiz answer."""
        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="a",
            time_taken_seconds=5.0,
        )

        event = api_gateway_event_with_body.copy()
        event["resource"] = "/quiz/answer"
        event["path"] = "/quiz/answer"
        event["httpMethod"] = "POST"
        event["body"] = json.dumps(answer_request.model_dump())
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        return event

    def test_submit_answer_success(self, handler, sample_event, mock_config):
        """Test successful answer submission."""
        with patch(
            "handlers.quiz_answer_api.handler.quiz_service"
        ) as mock_service:
            mock_response = QuizAnswerResponse(
                is_correct=True,
                points_earned=8.5,
                explanation="Really good",
                running_stats=QuizSessionProgress(
                    questions_answered=1,
                    correct_count=1,
                    total_score=8.5,
                    accuracy=1.0,
                    time_spent_seconds=5.0,
                ),
            )
            mock_service.submit_answer.return_value = mock_response

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["is_correct"] is True
            assert body_dict["points_earned"] == 8.5
            assert body_dict["running_stats"]["questions_answered"] == 1

    def test_submit_answer_incorrect(self, handler, sample_event, mock_config):
        """Test answer submission with incorrect answer."""
        with patch(
            "handlers.quiz_answer_api.handler.quiz_service"
        ) as mock_service:
            mock_response = QuizAnswerResponse(
                is_correct=False,
                points_earned=0.0,
                explanation="Really good",
                running_stats=QuizSessionProgress(
                    questions_answered=1,
                    correct_count=0,
                    total_score=0.0,
                    accuracy=0.0,
                    time_spent_seconds=10.0,
                ),
            )
            mock_service.submit_answer.return_value = mock_response

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["is_correct"] is False
            assert body_dict["points_earned"] == 0.0
