"""Tests for QuizConfig model and integration."""

import pytest
import os
from unittest.mock import patch

from models.config import QuizConfig


class TestQuizConfig:
    """Test QuizConfig model and configuration service integration."""

    def test_quiz_config_defaults(self):
        """Test QuizConfig default values."""
        config = QuizConfig()

        assert config.free_daily_limit == 3
        assert config.premium_unlimited is True
        assert config.questions_per_quiz == 10
        assert config.time_limit_seconds == 60
        assert config.points_per_correct == 10
        assert config.enable_time_bonus is True

    def test_quiz_config_custom_values(self):
        """Test QuizConfig with custom values."""
        config = QuizConfig(
            free_daily_limit=5,
            premium_unlimited=False,
            questions_per_quiz=15,
            time_limit_seconds=90,
            points_per_correct=15,
            enable_time_bonus=False
        )

        assert config.free_daily_limit == 5
        assert config.premium_unlimited is False
        assert config.questions_per_quiz == 15
        assert config.time_limit_seconds == 90
        assert config.points_per_correct == 15
        assert config.enable_time_bonus is False

    def test_quiz_config_validation(self):
        """Test QuizConfig field validation."""
        # Test with valid values
        config = QuizConfig(
            free_daily_limit=1,
            questions_per_quiz=1,
            time_limit_seconds=1,
            points_per_correct=1
        )

        assert config.free_daily_limit == 1
        assert config.questions_per_quiz == 1
        assert config.time_limit_seconds == 1
        assert config.points_per_correct == 1

    def test_config_service_loads_quiz_config(self):
        """Test ConfigService can load QuizConfig from environment."""
        from utils.config import ConfigService

        # Set environment variables
        os.environ["QUIZ_FREE_DAILY_LIMIT"] = "5"
        os.environ["QUIZ_QUESTIONS_PER_QUIZ"] = "15"
        os.environ["QUIZ_TIME_LIMIT_SECONDS"] = "90"
        os.environ["ENVIRONMENT"] = "test"

        try:
            config_service = ConfigService()
            quiz_config = config_service.get_config(QuizConfig)

            assert quiz_config.free_daily_limit == 5
            assert quiz_config.questions_per_quiz == 15
            assert quiz_config.time_limit_seconds == 90
            assert quiz_config.points_per_correct == 10  # Default value
            assert quiz_config.enable_time_bonus is True  # Default value

        finally:
            # Cleanup
            os.environ.pop("QUIZ_FREE_DAILY_LIMIT", None)
            os.environ.pop("QUIZ_QUESTIONS_PER_QUIZ", None)
            os.environ.pop("QUIZ_TIME_LIMIT_SECONDS", None)

    def test_config_service_quiz_config_defaults(self):
        """Test ConfigService uses defaults when env vars not set."""
        from utils.config import ConfigService

        # Ensure environment variables are not set
        os.environ.pop("QUIZ_FREE_DAILY_LIMIT", None)
        os.environ.pop("QUIZ_QUESTIONS_PER_QUIZ", None)
        os.environ.pop("QUIZ_TIME_LIMIT_SECONDS", None)
        os.environ["ENVIRONMENT"] = "test"

        try:
            config_service = ConfigService()
            quiz_config = config_service.get_config(QuizConfig)

            # Should use default values
            assert quiz_config.free_daily_limit == 3
            assert quiz_config.questions_per_quiz == 10
            assert quiz_config.time_limit_seconds == 60

        finally:
            # Cleanup
            os.environ.pop("QUIZ_FREE_DAILY_LIMIT", None)
            os.environ.pop("QUIZ_QUESTIONS_PER_QUIZ", None)
            os.environ.pop("QUIZ_TIME_LIMIT_SECONDS", None)

    def test_config_service_quiz_config_invalid_values(self):
        """Test ConfigService handles invalid environment variable values."""
        from utils.config import ConfigService

        # Set invalid environment variables
        os.environ["QUIZ_FREE_DAILY_LIMIT"] = "invalid"
        os.environ["QUIZ_QUESTIONS_PER_QUIZ"] = "not_a_number"
        os.environ["QUIZ_TIME_LIMIT_SECONDS"] = "also_invalid"
        os.environ["ENVIRONMENT"] = "test"

        try:
            config_service = ConfigService()

            # Should raise ValueError for invalid int conversion
            with pytest.raises(ValueError):
                config_service.get_config(QuizConfig)

        finally:
            # Cleanup
            os.environ.pop("QUIZ_FREE_DAILY_LIMIT", None)
            os.environ.pop("QUIZ_QUESTIONS_PER_QUIZ", None)
            os.environ.pop("QUIZ_TIME_LIMIT_SECONDS", None)

    @patch.dict(os.environ, {
        "QUIZ_FREE_DAILY_LIMIT": "0",
        "QUIZ_QUESTIONS_PER_QUIZ": "0",
        "QUIZ_TIME_LIMIT_SECONDS": "0",
        "ENVIRONMENT": "test"
    })
    def test_config_service_quiz_config_edge_values(self):
        """Test ConfigService with edge case values."""
        from utils.config import ConfigService

        config_service = ConfigService()
        quiz_config = config_service.get_config(QuizConfig)

        assert quiz_config.free_daily_limit == 0
        assert quiz_config.questions_per_quiz == 0
        assert quiz_config.time_limit_seconds == 0

    def test_quiz_config_serialization(self):
        """Test QuizConfig can be serialized to JSON."""
        config = QuizConfig(
            free_daily_limit=5,
            questions_per_quiz=15,
            time_limit_seconds=90
        )

        # Should be able to convert to dict
        config_dict = config.model_dump()

        assert config_dict["free_daily_limit"] == 5
        assert config_dict["questions_per_quiz"] == 15
        assert config_dict["time_limit_seconds"] == 90
        assert config_dict["premium_unlimited"] is True
        assert config_dict["points_per_correct"] == 10
        assert config_dict["enable_time_bonus"] is True

    def test_quiz_config_deserialization(self):
        """Test QuizConfig can be created from dict."""
        config_dict = {
            "free_daily_limit": 7,
            "premium_unlimited": False,
            "questions_per_quiz": 20,
            "time_limit_seconds": 120,
            "points_per_correct": 20,
            "enable_time_bonus": False
        }

        config = QuizConfig(**config_dict)

        assert config.free_daily_limit == 7
        assert config.premium_unlimited is False
        assert config.questions_per_quiz == 20
        assert config.time_limit_seconds == 120
        assert config.points_per_correct == 20
        assert config.enable_time_bonus is False

    def test_quiz_config_field_descriptions(self):
        """Test QuizConfig field descriptions are present."""
        config = QuizConfig()
        schema = config.model_json_schema()

        # Check that descriptions are present in schema
        properties = schema.get("properties", {})

        assert "description" in properties["free_daily_limit"]
        assert "description" in properties["premium_unlimited"]
        assert "description" in properties["questions_per_quiz"]
        assert "description" in properties["time_limit_seconds"]
        assert "description" in properties["points_per_correct"]
        assert "description" in properties["enable_time_bonus"]

    def test_quiz_config_immutability(self):
        """Test that QuizConfig fields are properly typed and validated."""
        # Test that we can't assign invalid types
        with pytest.raises(ValueError):
            QuizConfig(free_daily_limit="not_a_number")

        with pytest.raises(ValueError):
            QuizConfig(premium_unlimited="not_a_boolean")

        with pytest.raises(ValueError):
            QuizConfig(questions_per_quiz=-1)  # Negative numbers should fail validation
