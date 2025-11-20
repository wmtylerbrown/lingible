"""Tests for response utility functions."""

import pytest
import json
from datetime import datetime, timezone

from models.quiz import QuizHistory, QuizResult
from utils.exceptions import BusinessLogicError, UsageLimitExceededError
from utils.response import create_model_response, create_error_response


class TestResponseUtils:
    """Test response utility functions."""

    def test_create_success_response(self):
        """Test creating success response with Pydantic model."""
        history = QuizHistory(
            user_id="test_123",
            total_quizzes=1,
            average_score=85.0,
            best_score=100.0,
            total_correct=10,
            total_questions=10,
            accuracy_rate=1.0,
            quizzes_today=0,
            can_take_quiz=True,
        )

        response = create_model_response(history)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["user_id"] == "test_123"
        assert body["total_quizzes"] == 1

    def test_create_success_response_with_custom_status(self):
        """Test creating success response with custom status code."""
        history = QuizHistory(
            user_id="test",
            total_quizzes=1,
            average_score=85.0,
            best_score=100.0,
            total_correct=10,
            total_questions=10,
            accuracy_rate=1.0,
            quizzes_today=0,
            can_take_quiz=True,
        )

        response = create_model_response(history, status_code=201)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["user_id"] == "test"

    def test_create_error_response(self):
        """Test creating error response."""
        error = BusinessLogicError("Test error")

        response = create_error_response(error)

        assert response["statusCode"] == 400
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["message"] == "Test error"
        assert body["error_code"] == "BIZ_001"
        assert "timestamp" in body
        assert isinstance(body["timestamp"], str)  # ISO8601 string

    def test_create_error_response_with_details(self):
        """Test creating error response with usage limit details."""
        error = UsageLimitExceededError("quiz_questions", 10, 10)

        response = create_error_response(error)

        assert response["statusCode"] == 429
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["status_code"] == 429
        assert body["details"]["limit_type"] == "quiz_questions"
        assert body["details"]["current_usage"] == 10  # Should be int, not string
        assert body["details"]["limit"] == 10  # Should be int, not string
        assert isinstance(body["details"]["current_usage"], int)
        assert isinstance(body["details"]["limit"], int)

    def test_create_model_response_with_quiz_history(self):
        """Test create_model_response with QuizHistory model."""
        history = QuizHistory(
            user_id="test_user",
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

        response = create_model_response(history)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        # Body should be a JSON string from to_json()
        assert isinstance(response["body"], str)
        body_dict = json.loads(response["body"])
        assert body_dict["user_id"] == "test_user"
        assert body_dict["total_quizzes"] == 10

    def test_create_model_response_with_quiz_result(self):
        """Test create_model_response with QuizResult model."""
        result = QuizResult(
            session_id="session_123",
            score=25,
            total_possible=20,
            correct_count=2,
            total_questions=2,
            time_taken_seconds=45,
            share_text="Test share text",
            share_url=None,
        )

        response = create_model_response(result)

        assert response["statusCode"] == 200
        body_dict = json.loads(response["body"])
        assert body_dict["session_id"] == "session_123"
        assert body_dict["score"] == 25
        assert body_dict["correct_count"] == 2
