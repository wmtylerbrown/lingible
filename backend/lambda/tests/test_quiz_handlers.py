"""Tests for Quiz Lambda handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timezone, timedelta

from src.models.quiz import (
    QuizHistory,
    QuizResult,
    QuizDifficulty,
    QuizQuestionResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizSessionProgress,
    QuizEndRequest,
)
from src.models.users import UserTier
from src.utils.exceptions import ValidationError, InsufficientPermissionsError


class TestQuizHistoryAPIHandler:
    """Test quiz history API handler."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.quiz_history_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for quiz history."""
        return {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "headers": {
                "Authorization": "Bearer fake_token",
            },
        }

    def test_get_quiz_history_success_premium(self, handler, sample_event, mock_config):
        """Test successful quiz history retrieval for premium user."""
        with patch(
            "src.handlers.quiz_history_api.handler.quiz_service"
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
            "src.handlers.quiz_history_api.handler.quiz_service"
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
            "src.handlers.quiz_history_api.handler.quiz_service"
        ) as mock_service:
            mock_service.check_quiz_eligibility.side_effect = Exception("Database error")

            response = handler(sample_event, {})

            assert response["statusCode"] == 500
            body_dict = json.loads(response["body"])
            assert body_dict["success"] is False
            assert "error" in body_dict or "message" in body_dict


# ===== Stateless API Handler Tests =====

class TestQuizQuestionAPIHandler:
    """Test GET /quiz/question handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.quiz_challenge_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for quiz question."""
        return {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "queryStringParameters": {
                "difficulty": "beginner",
            },
            "headers": {
                "Authorization": "Bearer fake_token",
            },
        }

    def test_get_question_success(self, handler, sample_event, mock_config):
        """Test successful question retrieval."""
        with patch(
            "src.handlers.quiz_challenge_api.handler.quiz_service"
        ) as mock_service:
            from src.models.quiz import QuizQuestion, QuizOption

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

    def test_get_question_default_difficulty(self, handler, mock_config):
        """Test question retrieval with default difficulty."""
        event = {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "queryStringParameters": None,  # No difficulty specified
            "headers": {
                "Authorization": "Bearer fake_token",
            },
        }

        with patch(
            "src.handlers.quiz_challenge_api.handler.quiz_service"
        ) as mock_service:
            from src.models.quiz import QuizQuestion, QuizOption, QuizQuestionResponse

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


class TestQuizAnswerAPIHandler:
    """Test POST /quiz/answer handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.quiz_submit_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for quiz answer."""
        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="a",
            time_taken_seconds=5.0,
        )

        return {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "body": json.dumps(answer_request.model_dump()),
            "headers": {
                "Authorization": "Bearer fake_token",
                "Content-Type": "application/json",
            },
        }

    def test_submit_answer_success(self, handler, sample_event, mock_config):
        """Test successful answer submission."""
        with patch(
            "src.handlers.quiz_submit_api.handler.quiz_service"
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
            "src.handlers.quiz_submit_api.handler.quiz_service"
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


class TestQuizProgressAPIHandler:
    """Test GET /quiz/progress handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.quiz_progress_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for quiz progress."""
        return {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "queryStringParameters": {
                "session_id": "session_123",
            },
            "headers": {
                "Authorization": "Bearer fake_token",
            },
        }

    def test_get_progress_success(self, handler, sample_event, mock_config):
        """Test successful progress retrieval."""
        with patch(
            "src.handlers.quiz_progress_api.handler.quiz_service"
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

    def test_get_progress_missing_session_id(self, handler, mock_config):
        """Test progress retrieval without session_id."""
        event = {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "queryStringParameters": None,  # No session_id
            "headers": {
                "Authorization": "Bearer fake_token",
            },
        }

        response = handler(event, {})

        # Should return validation error
        assert response["statusCode"] == 422


class TestQuizEndAPIHandler:
    """Test POST /quiz/end handler (stateless API)."""

    @pytest.fixture
    def handler(self):
        """Import the handler."""
        from src.handlers.quiz_end_api.handler import handler
        return handler

    @pytest.fixture
    def sample_event(self):
        """Sample API Gateway event for quiz end."""
        end_request = QuizEndRequest(session_id="session_123")

        return {
            "requestContext": {
                "authorizer": {
                    "user_id": "test_user_123",
                },
                "requestId": "req_123",
            },
            "body": json.dumps(end_request.model_dump()),
            "headers": {
                "Authorization": "Bearer fake_token",
                "Content-Type": "application/json",
            },
        }

    def test_end_session_success(self, handler, sample_event, mock_config):
        """Test successful session end."""
        with patch(
            "src.handlers.quiz_end_api.handler.quiz_service"
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
