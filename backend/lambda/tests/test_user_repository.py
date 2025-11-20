from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from models.quiz import QuizSessionRecord, QuizStats, QuizSessionStatus, QuizDifficulty
from models.translations import UsageLimit
from models.users import User, UserStatus, UserTier
from repositories.user_repository import UserRepository
from utils.exceptions import SystemError as LingibleSystemError


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def test_get_user_returns_typed_model(users_table: str, moto_dynamodb) -> None:
    table = moto_dynamodb.Table(users_table)
    created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    updated_at = created_at + timedelta(hours=1)

    table.put_item(
        Item={
            "PK": "USER#user-123",
            "SK": "PROFILE",
            "user_id": "user-123",
            "email": "test@example.com",
            "username": "tester",
            "tier": UserTier.PREMIUM,
            "status": "active",
            "slang_submitted_count": Decimal("2"),
            "slang_approved_count": Decimal("1"),
            "created_at": _iso(created_at),
            "updated_at": _iso(updated_at),
        }
    )

    repository = UserRepository()
    user = repository.get_user("user-123")

    assert user is not None
    assert user.user_id == "user-123"
    assert user.tier is UserTier.PREMIUM
    assert user.created_at == created_at
    assert user.slang_submitted_count == 2
    assert user.slang_approved_count == 1


def test_increment_usage_creates_usage_record(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()

    assert repository.increment_usage("usage-user", UserTier.PREMIUM) is True

    table = moto_dynamodb.Table(users_table)
    item = table.get_item(Key={"PK": "USER#usage-user", "SK": "USAGE#LIMITS"})["Item"]

    assert int(item["daily_used"]) == 1
    assert item["tier"] == UserTier.PREMIUM
    assert "reset_daily_at" in item


def test_get_usage_limits_default_reset(users_table: str, moto_dynamodb) -> None:
    table = moto_dynamodb.Table(users_table)
    table.put_item(
        Item={
            "PK": "USER#limit-user",
            "SK": "USAGE#LIMITS",
            "tier": UserTier.FREE,
            "daily_used": Decimal("3"),
            # intentionally omit reset_daily_at to exercise default branch
        }
    )

    repository = UserRepository()
    limits = repository.get_usage_limits("limit-user")

    assert limits is not None
    assert limits.tier is UserTier.FREE
    assert limits.daily_used == 3
    assert isinstance(limits.reset_daily_at, datetime)
    assert limits.reset_daily_at > datetime.now(timezone.utc) - timedelta(days=1)


def make_user(user_id: str = "user-1", *, tier: UserTier = UserTier.FREE) -> User:
    return User(
        user_id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        tier=tier,
        status=UserStatus.ACTIVE,
    )


def test_increment_daily_quiz_count(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    first = repository.increment_daily_quiz_count("quiz-count-user")
    second = repository.increment_daily_quiz_count("quiz-count-user")
    assert first == 1
    assert second == 2


def test_delete_daily_quiz_count(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    repository.increment_daily_quiz_count("delete-quiz-user")
    assert repository.delete_daily_quiz_count("delete-quiz-user") is True
    table = moto_dynamodb.Table(users_table)
    today = datetime.now(timezone.utc).date().isoformat()
    key = {"PK": f"USER#delete-quiz-user", "SK": f"QUIZ_DAILY#{today}"}
    assert "Item" not in table.get_item(Key=key)


def test_increment_usage_rolls_over_when_reset_expired(users_table: str, moto_dynamodb) -> None:
    table = moto_dynamodb.Table(users_table)
    table.put_item(
        Item={
            "PK": "USER#rollover",
            "SK": "USAGE#LIMITS",
            "tier": UserTier.FREE,
            "daily_used": Decimal("5"),
            "reset_daily_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }
    )

    repository = UserRepository()
    assert repository.increment_usage("rollover") is True

    item = table.get_item(Key={"PK": "USER#rollover", "SK": "USAGE#LIMITS"})["Item"]
    assert int(item["daily_used"]) == 1


def test_quiz_session_create_update_complete(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()

    # Create session
    repository.create_quiz_session(
        user_id="quiz_user",
        session_id="session_1",
        difficulty=QuizDifficulty.INTERMEDIATE.value,
    )
    active = repository.get_active_quiz_session("quiz_user")
    assert active is not None
    assert active.session_id == "session_1"
    session = repository.get_quiz_session("quiz_user", "session_1")
    assert session is not None
    assert session.session_id == "session_1"

    # Update session progress with total_score (float)
    repository.update_quiz_session(
        user_id="quiz_user",
        session_id="session_1",
        total_score=25.5,  # float value
        correct_answers={"q1": "a"},
        term_names={"q1": "rizz"},
        used_wrong_options=["wrong1"],
    )
    session = repository.get_quiz_session("quiz_user", "session_1")
    assert session is not None
    assert session.used_wrong_options == ["wrong1"]
    assert session.total_score == 25.5  # Should be float when read back

    # Complete session
    repository.update_quiz_session(
        user_id="quiz_user",
        session_id="session_1",
        total_score=50.0,  # float value
        correct_answers={"q1": "a", "q2": "b"},
        term_names={"q1": "rizz", "q2": "yeet"},
        used_wrong_options=["wrong1", "wrong2"],
    )
    session = repository.get_quiz_session("quiz_user", "session_1")
    assert session is not None
    assert session.status is QuizSessionStatus.ACTIVE
    assert session.total_score == 50.0  # Should be float when read back

    assert repository.delete_quiz_session("quiz_user", "session_1") is True
    assert repository.get_quiz_session("quiz_user", "session_1") is None


def test_finalize_quiz_session_updates_stats(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    expected_stats = QuizStats(
        total_quizzes=1,
        total_correct=4,
        total_questions=5,
        average_score=80.0,
        best_score=90.0,
        accuracy_rate=0.8,
    )

    repository.update_quiz_stats = MagicMock(return_value=expected_stats)
    repository.delete_quiz_session = MagicMock(return_value=True)

    stats = repository.finalize_quiz_session(
        user_id="final_user",
        session_id="session_final",
        questions_answered=5,
        correct_count=4,
        total_score=80.0,
        total_possible=100.0,
    )

    assert stats is expected_stats
    repository.update_quiz_stats.assert_called_once()
    repository.delete_quiz_session.assert_called_once_with("final_user", "session_final")


def test_user_repository_crud_flow(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    user = make_user("crud-user")

    assert repository.create_user(user) is True
    fetched = repository.get_user("crud-user")
    assert fetched is not None
    assert fetched.email == user.email

    updated = user.model_copy(update={"tier": UserTier.PREMIUM})
    assert repository.update_user(updated) is True
    fetched_after_update = repository.get_user("crud-user")
    assert fetched_after_update is not None
    assert fetched_after_update.tier is UserTier.PREMIUM

    assert repository.delete_user("crud-user") is True
    assert repository.get_user("crud-user") is None


def test_usage_limit_workflow(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    usage = UsageLimit(
        tier=UserTier.FREE,
        daily_used=3,
        reset_daily_at=datetime.now(timezone.utc) + timedelta(hours=12),
    )

    assert repository.update_usage_limits("usage-user", usage) is True
    stored = repository.get_usage_limits("usage-user")
    assert stored is not None
    assert stored.daily_used == 3

    assert repository.reset_daily_usage("usage-user") is True
    reset_limits = repository.get_usage_limits("usage-user")
    assert reset_limits is not None
    assert reset_limits.daily_used == 0


def test_get_quiz_stats_defaults(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    stats = repository.get_quiz_stats("unknown")
    assert isinstance(stats, QuizStats)
    assert stats.total_quizzes == 0


def test_delete_user_removes_records(users_table: str, moto_dynamodb) -> None:
    table = moto_dynamodb.Table(users_table)
    table.put_item(
        Item={"PK": "USER#delete", "SK": "PROFILE", "user_id": "delete"}
    )
    table.put_item(
        Item={"PK": "USER#delete", "SK": "USAGE#LIMITS", "daily_used": 1}
    )

    repository = UserRepository()
    assert repository.delete_user("delete") is True

    response = table.get_item(Key={"PK": "USER#delete", "SK": "PROFILE"})
    assert "Item" not in response


def test_increment_slang_counts(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    user = make_user("slang-user")
    repository.create_user(user)

    assert repository.increment_slang_submitted("slang-user") is True
    assert repository.increment_slang_approved("slang-user") is True

    fetched = repository.get_user("slang-user")
    assert fetched is not None
    assert fetched.slang_submitted_count == 1
    assert fetched.slang_approved_count == 1


def test_delete_all_quiz_data(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    repository.create_quiz_session("cleanup", "session_cleanup", QuizDifficulty.BEGINNER.value)
    repository.increment_daily_quiz_count("cleanup")

    table = moto_dynamodb.Table(users_table)
    table.put_item(
        Item={
            "PK": "USER#cleanup",
            "SK": repository.QUIZ_STATS_SK,
            "total_quizzes": Decimal("1"),
            "total_correct": Decimal("1"),
            "total_questions": Decimal("1"),
            "total_score_sum": Decimal("10"),
            "total_possible_sum": Decimal("10"),
            "best_score": Decimal("100"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    repository.delete_all_quiz_data("cleanup")

    response = table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": "USER#cleanup"},
    )
    assert response.get("Count", 0) == 0


def test_create_user_raises_system_error_on_failure(monkeypatch, users_table: str) -> None:
    repository = UserRepository()
    user = make_user("error-user")

    def raise_put(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    with pytest.raises(LingibleSystemError):
        repository.create_user(user)


def test_get_user_returns_none_on_exception(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_get(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get)
    assert repository.get_user("who") is None


def test_update_user_raises_system_error_on_failure(monkeypatch, users_table: str) -> None:
    repository = UserRepository()
    user = make_user("update-user")

    def raise_put(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    with pytest.raises(LingibleSystemError):
        repository.update_user(user)


def test_update_usage_limits_raises_system_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()
    usage = UsageLimit(
        tier=UserTier.FREE,
        daily_used=1,
        reset_daily_at=datetime.now(timezone.utc),
    )

    def raise_put(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    with pytest.raises(LingibleSystemError):
        repository.update_usage_limits("usage", usage)


def test_get_usage_limits_returns_none_on_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_get(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get)
    assert repository.get_usage_limits("usage") is None


def test_increment_usage_raises_system_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    with pytest.raises(LingibleSystemError):
        repository.increment_usage("usage-user")


def test_reset_daily_usage_raises_system_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    with pytest.raises(LingibleSystemError):
        repository.reset_daily_usage("reset-user")


def test_delete_user_raises_system_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_delete(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "delete_item", raise_delete)
    with pytest.raises(LingibleSystemError):
        repository.delete_user("delete-user")


def test_delete_user_logs_error_when_cleanup_fails(monkeypatch, users_table: str) -> None:
    repository = UserRepository()
    table = repository.table

    def fake_delete(*_: Any, **__: Any) -> None:
        return None

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(table, "delete_item", fake_delete)
    monkeypatch.setattr(table, "query", raise_query)
    assert repository.delete_user("cleanup-user") is True


def test_get_daily_quiz_count_returns_zero_on_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_get(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get)
    today = datetime.now(timezone.utc).date().isoformat()
    assert repository.get_daily_quiz_count("user", today) == 0


def test_increment_daily_quiz_count_returns_one_on_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert repository.increment_daily_quiz_count("user") == 1


def test_increment_slang_counters_handle_errors(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert repository.increment_slang_submitted("user") is False
    assert repository.increment_slang_approved("user") is False


def test_update_quiz_stats_accumulates(users_table: str) -> None:
    """Test that quiz stats accumulate correctly across multiple updates."""
    repository = UserRepository()

    first = repository.update_quiz_stats(
        "stats-user",
        correct_count=3,
        questions_answered=5,
        total_score=80.0,
        total_possible=100.0,
    )
    assert first.total_quizzes == 1

    second = repository.update_quiz_stats(
        "stats-user",
        correct_count=2,
        questions_answered=5,
        total_score=70.0,
        total_possible=100.0,
    )
    assert second.total_quizzes == 2

    fetched = repository.get_quiz_stats("stats-user")
    assert fetched.total_quizzes == 2
    assert fetched.total_correct == 5


def test_update_quiz_stats_stores_decimal_not_float(users_table: str, moto_dynamodb) -> None:
    """Test that update_quiz_stats stores Decimal types, not floats (DynamoDB requirement)."""
    from decimal import Decimal

    repository = UserRepository()
    captured_items: list[dict[str, Any]] = []
    original_put = repository.table.put_item

    def capture_put_item(*args: Any, **kwargs: Any) -> Any:
        item = kwargs.get("Item", {})
        captured_items.append(item.copy())
        # Verify no floats in the item
        for key, value in item.items():
            assert not isinstance(
                value, float
            ), f"Found float value for key '{key}': {value}. DynamoDB requires Decimal types."
        return original_put(*args, **kwargs)

    repository.table.put_item = capture_put_item  # type: ignore[assignment]

    repository.update_quiz_stats(
        "test-user",
        correct_count=5,
        questions_answered=10,
        total_score=85.5,
        total_possible=100.0,
    )

    assert len(captured_items) == 1
    item = captured_items[0]
    # Verify best_score is Decimal, not float
    assert isinstance(item.get("best_score"), Decimal), "best_score must be Decimal, not float"
    assert isinstance(item.get("total_score_sum"), Decimal), "total_score_sum must be Decimal"
    assert isinstance(item.get("total_possible_sum"), Decimal), "total_possible_sum must be Decimal"


def test_quiz_stats_api_returns_float_not_decimal(users_table: str, moto_dynamodb) -> None:
    """Test that QuizStats returned from repository converts Decimal to float for API compatibility."""
    repository = UserRepository()

    # Create stats with float values
    stats = repository.update_quiz_stats(
        "api-test-user",
        correct_count=8,
        questions_answered=10,
        total_score=80.0,
        total_possible=100.0,
    )

    # Verify the returned model has float fields (API-compatible)
    assert isinstance(stats.average_score, float), "average_score should be float for API"
    assert isinstance(stats.best_score, float), "best_score should be float for API"
    assert isinstance(stats.accuracy_rate, float), "accuracy_rate should be float for API"

    # Verify serialize_model() returns float (used by API responses)
    api_dict = stats.serialize_model()
    assert isinstance(api_dict["average_score"], float)
    assert isinstance(api_dict["best_score"], float)
    assert isinstance(api_dict["accuracy_rate"], float)


def test_numeric_helpers_handle_various_inputs() -> None:
    repository = UserRepository()
    assert repository._to_int(Decimal("2.0")) == 2
    assert repository._to_float(Decimal("1.5")) == 1.5
    assert repository._to_decimal(1.25) == Decimal("1.25")


def test_get_daily_quiz_count_reads_decimal(users_table: str, moto_dynamodb) -> None:
    repository = UserRepository()
    today = datetime.now(timezone.utc).date().isoformat()
    table = moto_dynamodb.Table(users_table)
    table.put_item(
        Item={
            "PK": "USER#quiz-dec",
            "SK": f"QUIZ_DAILY#{today}",
            "quiz_count": Decimal("3"),
        }
    )
    assert repository.get_daily_quiz_count("quiz-dec", today) == 3


def test_increment_daily_quiz_count_handles_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_update(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert repository.increment_daily_quiz_count("error-user") == 1


def test_delete_daily_quiz_count_handles_error(monkeypatch, users_table: str) -> None:
    repository = UserRepository()

    def raise_delete(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "delete_item", raise_delete)
    assert repository.delete_daily_quiz_count("error-user") is False
