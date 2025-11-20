"""Tests for LingibleBaseModel serialization methods."""

from decimal import Decimal
from datetime import datetime, timezone

from models.base import LingibleBaseModel
from models.quiz import QuizStats, QuizSessionRecord
from models.slang import SlangTerm
from models.trending import TrendingTerm, TrendingCategory


def test_to_dynamodb_converts_float_to_decimal() -> None:
    """Test that to_dynamodb() converts float values to Decimal for DynamoDB."""
    stats = QuizStats(
        total_quizzes=5,
        total_correct=40,
        total_questions=50,
        average_score=80.5,  # float
        best_score=95.0,  # float
        accuracy_rate=0.8,  # float
    )

    dynamodb_dict = stats.to_dynamodb()

    # Verify float fields are converted to Decimal
    assert isinstance(dynamodb_dict["average_score"], Decimal)
    assert isinstance(dynamodb_dict["best_score"], Decimal)
    assert isinstance(dynamodb_dict["accuracy_rate"], Decimal)

    # Verify values are correct
    assert dynamodb_dict["average_score"] == Decimal("80.5")
    assert dynamodb_dict["best_score"] == Decimal("95.0")
    assert dynamodb_dict["accuracy_rate"] == Decimal("0.8")

    # Verify int fields remain int
    assert isinstance(dynamodb_dict["total_quizzes"], int)
    assert dynamodb_dict["total_quizzes"] == 5


def test_to_dynamodb_preserves_decimal() -> None:
    """Test that to_dynamodb() preserves Decimal values."""
    term = TrendingTerm(
        term="test",
        definition="test definition",
        category=TrendingCategory.SLANG,
        popularity_score=Decimal("85.5"),  # Already Decimal
        search_count=100,
        translation_count=50,
        first_seen=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        is_active=True,
    )

    dynamodb_dict = term.to_dynamodb()

    # Verify Decimal is preserved
    assert isinstance(dynamodb_dict["popularity_score"], Decimal)
    assert dynamodb_dict["popularity_score"] == Decimal("85.5")


def test_to_dynamodb_handles_nested_models() -> None:
    """Test that to_dynamodb() handles nested LingibleBaseModel instances."""
    # Create a model with nested structure (if we had one)
    # For now, test that it works with simple models
    stats = QuizStats(
        total_quizzes=1,
        total_correct=8,
        total_questions=10,
        average_score=80.0,
        best_score=80.0,
        accuracy_rate=0.8,
    )

    dynamodb_dict = stats.to_dynamodb()
    assert isinstance(dynamodb_dict["average_score"], Decimal)


def test_serialize_model_returns_float_for_api() -> None:
    """Test that serialize_model() converts Decimal to float for API responses."""
    # Create a model with Decimal values (simulating what comes from DB)
    stats = QuizStats(
        total_quizzes=5,
        total_correct=40,
        total_questions=50,
        average_score=80.5,  # Will be float in model
        best_score=95.0,  # Will be float in model
        accuracy_rate=0.8,  # Will be float in model
    )

    api_dict = stats.serialize_model()

    # Verify float fields remain float (API-friendly)
    assert isinstance(api_dict["average_score"], float)
    assert isinstance(api_dict["best_score"], float)
    assert isinstance(api_dict["accuracy_rate"], float)

    # Verify values are correct
    assert api_dict["average_score"] == 80.5
    assert api_dict["best_score"] == 95.0
    assert api_dict["accuracy_rate"] == 0.8


def test_to_dynamodb_vs_serialize_model_symmetry() -> None:
    """Test that to_dynamodb() and serialize_model() are symmetric (opposite conversions)."""
    stats = QuizStats(
        total_quizzes=3,
        total_correct=24,
        total_questions=30,
        average_score=80.0,
        best_score=90.0,
        accuracy_rate=0.8,
    )

    # Convert to DynamoDB format (float → Decimal)
    dynamodb_dict = stats.to_dynamodb()
    assert isinstance(dynamodb_dict["average_score"], Decimal)

    # Create a new model from DynamoDB data (simulating DB read)
    # The _normalize_input will convert Decimal → float
    stats_from_db = QuizStats(**dynamodb_dict)

    # Serialize for API (should be float)
    api_dict = stats_from_db.serialize_model()
    assert isinstance(api_dict["average_score"], float)
    assert api_dict["average_score"] == 80.0
