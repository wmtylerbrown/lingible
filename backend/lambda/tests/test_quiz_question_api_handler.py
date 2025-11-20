"""Tests for quiz question API handler."""

import os
import pytest
from unittest.mock import Mock, patch
import json

from models.quiz import (
    QuizDifficulty,
    QuizQuestionResponse,
    QuizQuestion,
    QuizOption,
)


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


class TestQuizQuestionAPIHandler:
    """Test GET /quiz/question handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from handlers.quiz_question_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self, api_gateway_event_with_query_params):
        """Sample API Gateway event for quiz question."""
        event = api_gateway_event_with_query_params.copy()
        event["resource"] = "/quiz/question"
        event["path"] = "/quiz/question"
        event["httpMethod"] = "GET"
        event["queryStringParameters"] = {"difficulty": "beginner"}
        event["multiValueQueryStringParameters"] = {"difficulty": ["beginner"]}
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"
        return event

    def test_get_question_success(self, handler, sample_event, mock_config):
        """Test successful question retrieval."""
        with patch(
            "handlers.quiz_question_api.handler.quiz_service"
        ) as mock_service:
            mock_question = QuizQuestion(
                question_id="q1",
                slang_term="bussin",
                question_text="What does 'bussin' mean?",
                options=[
                    QuizOption(id="a", text="Really good"),
                    QuizOption(id="b", text="Bad"),
                    QuizOption(id="c", text="Okay"),
                    QuizOption(id="d", text="Average"),
                ],
            )

            mock_response = QuizQuestionResponse(
                session_id="session_123",
                question=mock_question,
            )
            mock_service.get_next_question.return_value = mock_response

            response = handler(sample_event, {})

            assert response["statusCode"] == 200
            body_dict = json.loads(response["body"])
            assert body_dict["session_id"] == "session_123"
            assert body_dict["question"]["slang_term"] == "bussin"
            assert len(body_dict["question"]["options"]) == 4

    def test_get_question_default_difficulty(self, handler, mock_config, api_gateway_event_with_query_params):
        """Test question retrieval with default difficulty."""
        event = api_gateway_event_with_query_params.copy()
        event["resource"] = "/quiz/question"
        event["path"] = "/quiz/question"
        event["httpMethod"] = "GET"
        event["queryStringParameters"] = None  # No difficulty specified
        event["multiValueQueryStringParameters"] = None
        event["requestContext"]["authorizer"]["claims"]["sub"] = "test_user_123"

        with patch(
            "handlers.quiz_question_api.handler.quiz_service"
        ) as mock_service:
            mock_response = QuizQuestionResponse(
                session_id="session_123",
                question=QuizQuestion(
                    question_id="q1",
                    slang_term="test",
                    question_text="Test?",
                    options=[QuizOption(id="a", text="Test")],
                ),
            )
            mock_service.get_next_question.return_value = mock_response

            response = handler(event, {})

            assert response["statusCode"] == 200
            # Should default to BEGINNER
            mock_service.get_next_question.assert_called_once()
            call_args = mock_service.get_next_question.call_args
            assert call_args[0][1] == QuizDifficulty.BEGINNER
