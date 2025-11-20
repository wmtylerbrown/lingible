from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from models.config import QuizConfig
from models.quiz import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizCategory,
    QuizDifficulty,
    QuizHistory,
    QuizOption,
    QuizQuestion,
    QuizQuestionResponse,
    QuizSessionProgress,
    QuizSessionRecord,
    QuizSessionStatus,
    QuizStats,
    QuizResult,
)
from models.slang import SlangTerm
from models.users import UserTier
from services.quiz_service import QuizService
from utils.exceptions import UsageLimitExceededError, ValidationError
from utils.response import create_model_response


class DummyQuizConfigService:
    def __init__(self) -> None:
        self._config = QuizConfig(
            free_daily_limit=2,
            premium_unlimited=True,
            questions_per_quiz=5,
            time_limit_seconds=300,
            points_per_correct=10,
            enable_time_bonus=True,
        )

    def get_config(self, config_type):
        if config_type is QuizConfig:
            return self._config
        raise ValueError(config_type)


@pytest.fixture(autouse=True)
def reset_quiz_service_cache():
    QuizService._wrong_answer_pools = {}
    QuizService._pools_loaded = False
    yield
    QuizService._wrong_answer_pools = {}
    QuizService._pools_loaded = False


@pytest.fixture
def stats() -> QuizStats:
    return QuizStats(
        total_quizzes=10,
        average_score=7.5,
        best_score=10.0,
        total_correct=40,
        total_questions=50,
        accuracy_rate=0.8,
    )


def _build_service(user_tier: UserTier, quizzes_today: int, quiz_stats: QuizStats, active_session=None):
    dummy_config = DummyQuizConfigService()

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_daily_quiz_count.return_value = quizzes_today
        user_repo.get_quiz_stats.return_value = quiz_stats
        user_repo.get_active_quiz_session.return_value = active_session

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=user_tier)

        service = QuizService()
        return service, user_repo, user_service


def test_check_quiz_eligibility_blocks_free_user_at_limit(stats: QuizStats) -> None:
    service, user_repo, _ = _build_service(UserTier.FREE, quizzes_today=2, quiz_stats=stats)

    result = service.check_quiz_eligibility("user-123")

    assert result.can_take_quiz is False
    assert "Daily limit" in (result.reason or "")
    user_repo.get_daily_quiz_count.assert_called_once()


def test_check_quiz_eligibility_allows_premium(stats: QuizStats) -> None:
    service, user_repo, _ = _build_service(UserTier.PREMIUM, quizzes_today=99, quiz_stats=stats)

    result = service.check_quiz_eligibility("user-123")

    assert result.can_take_quiz is True
    assert result.reason is None
    user_repo.get_daily_quiz_count.assert_called_once()


def test_calculate_question_points_increases_with_speed() -> None:
    dummy_config = DummyQuizConfigService()

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository"), \
         patch("services.quiz_service.UserService"):
        service = QuizService()

    fast_points = service._calculate_question_points(is_correct=True, time_taken_seconds=5)
    slow_points = service._calculate_question_points(is_correct=True, time_taken_seconds=25)
    miss_points = service._calculate_question_points(is_correct=False, time_taken_seconds=5)

    assert fast_points > slow_points
    assert miss_points == 0.0


def test_quiz_question_response_serialization_matches_api_contract() -> None:
    question = QuizQuestion(
        question_id="q1",
        slang_term="rizz",
        question_text="What does 'rizz' mean?",
        options=[
            QuizOption(id="a", text="Charisma"),
            QuizOption(id="b", text="Confidence"),
            QuizOption(id="c", text="Energy"),
            QuizOption(id="d", text="Style"),
        ],
        context_hint="He's got mad rizz.",
    )
    response = QuizQuestionResponse(session_id="session123", question=question)

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["session_id"] == "session123"
    assert body["question"]["question_id"] == "q1"
    assert len(body["question"]["options"]) == 4
    assert body["question"]["options"][0]["id"] == "a"


def test_quiz_answer_response_serialization_matches_api_contract() -> None:
    running_stats = QuizSessionProgress(
        questions_answered=3,
        correct_count=2,
        total_score=25.0,
        accuracy=0.66,
        time_spent_seconds=42.5,
    )
    response = QuizAnswerResponse(
        is_correct=True,
        points_earned=8.5,
        explanation="Rizz means charisma.",
        running_stats=running_stats,
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["is_correct"] is True
    assert body["points_earned"] == 8.5
    assert body["running_stats"]["accuracy"] == running_stats.accuracy
    assert body["running_stats"]["questions_answered"] == 3
    # Verify float types are returned (not Decimal) for API compatibility
    assert isinstance(body["points_earned"], float), "API must return float, not Decimal"
    assert isinstance(body["running_stats"]["total_score"], float), "API must return float, not Decimal"
    assert isinstance(body["running_stats"]["accuracy"], float), "API must return float, not Decimal"
    assert isinstance(body["running_stats"]["time_spent_seconds"], float), "API must return float, not Decimal"


def test_quiz_result_serialization_matches_api_contract() -> None:
    result = QuizResult(
        session_id="session-end",
        score=42.0,
        total_possible=50.0,
        correct_count=8,
        total_questions=10,
        time_taken_seconds=120.5,
        share_text="I scored 42!",
        share_url="https://example.com/share",
    )

    envelope = create_model_response(result)
    body = json.loads(envelope["body"])

    assert body["session_id"] == "session-end"
    assert body["score"] == 42.0
    assert body["total_questions"] == 10
    assert body["share_url"] == "https://example.com/share"
    # Verify float types are returned (not Decimal) for API compatibility
    assert isinstance(body["score"], float), "API must return float, not Decimal"
    assert isinstance(body["total_possible"], float), "API must return float, not Decimal"
    assert isinstance(body["time_taken_seconds"], float), "API must return float, not Decimal"


def test_quiz_history_serialization_matches_api_contract() -> None:
    history = QuizHistory(
        user_id="user-quiz",
        total_quizzes=12,
        average_score=8.5,
        best_score=10.0,
        total_correct=60,
        total_questions=70,
        accuracy_rate=0.86,
        quizzes_today=2,
        can_take_quiz=True,
        reason=None,
    )

    envelope = create_model_response(history)
    body = json.loads(envelope["body"])

    assert body["user_id"] == "user-quiz"
    assert body["can_take_quiz"] is True
    assert body["accuracy_rate"] == history.accuracy_rate
    # Verify float types are returned (not Decimal) for API compatibility
    assert isinstance(body["average_score"], float), "API must return float, not Decimal"
    assert isinstance(body["best_score"], float), "API must return float, not Decimal"
    assert isinstance(body["accuracy_rate"], float), "API must return float, not Decimal"


def _make_slang_term() -> SlangTerm:
    return SlangTerm(
        term="rizz",
        gloss="Charisma",
        variants=["riz"],
        tags=["popular"],
        examples=["He's got mad rizz."],
        sources={"community": 5},
        categories=[QuizCategory.SOCIAL.value],
        is_quiz_eligible=True,
        quiz_category=QuizCategory.SOCIAL,
        quiz_difficulty=QuizDifficulty.BEGINNER,
    )


def test_get_next_question_creates_session_when_none_exists(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    term = _make_slang_term()
    session_record = QuizSessionRecord(
        session_id="session_abc",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository") as term_repo_cls, \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        term_repo = term_repo_cls.return_value
        term_repo.get_wrong_answer_pool.return_value = ["confidence", "energy", "vibe", "charisma"]
        term_repo.get_quiz_eligible_terms.return_value = [term]

        user_repo = user_repo_cls.return_value
        user_repo.get_daily_quiz_count.return_value = 0
        user_repo.get_quiz_stats.return_value = stats
        user_repo.get_active_quiz_session.return_value = None
        user_repo.get_quiz_session.return_value = session_record

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.PREMIUM)

        service = QuizService()
        response = service.get_next_question("user-123")

    assert response.session_id.startswith("session_")
    assert isinstance(response.question, QuizQuestion)
    assert {opt.id for opt in response.question.options} == {"a", "b", "c", "d"}
    user_repo.create_quiz_session.assert_called_once()
    user_repo.update_quiz_session.assert_called_once()


def test_get_next_question_raises_when_free_user_hits_limit(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    active_session = QuizSessionRecord(
        session_id="active-session",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        questions_answered=5,
        correct_count=4,
        total_score=35.0,
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_daily_quiz_count.return_value = dummy_config.get_config(QuizConfig).free_daily_limit
        user_repo.get_active_quiz_session.return_value = active_session

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.FREE)

        service = QuizService()

        with pytest.raises(UsageLimitExceededError):
            service.get_next_question("user-123")

        # Session should be finalized when limit is reached
        user_repo.finalize_quiz_session.assert_called_once_with(
            user_id="user-123",
            session_id="active-session",
            questions_answered=5,
            correct_count=4,
            total_score=35.0,
            total_possible=50.0,
        )


def test_generate_wrong_options_falls_back_to_category():
    dummy_config = DummyQuizConfigService()
    term = _make_slang_term()

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository") as term_repo_cls, \
         patch("services.quiz_service.UserRepository"), \
         patch("services.quiz_service.UserService"):

        term_repo = term_repo_cls.return_value
        term_repo.get_terms_by_category.return_value = [term]

        service = QuizService()
        wrong = service._generate_wrong_options(term, used_wrong_options=set())

    assert len(wrong) == 3
    assert term.meaning not in wrong


def test_normalize_answer_text_handles_multiple_meanings() -> None:
    service = QuizService.__new__(QuizService)
    assert service._normalize_answer_text("Cool; stylish; charismatic") == "Cool"
    assert service._normalize_answer_text("lol") == "Lol"
    assert service._normalize_answer_text("") == ""


def test_format_multiple_choice_correct_option_id_after_shuffle() -> None:
    """Test that correct_option_id actually points to the correct answer after shuffling.

    This test is critical - it verifies that after shuffling, the correct_option_id
    actually corresponds to the option with the correct answer text. Without this,
    we could have a bug where correct_option_id is always "a" even after shuffling.
    """
    dummy_config = DummyQuizConfigService()
    term = _make_slang_term()
    # Override the meaning to something specific we can check
    term = term.model_copy(update={"gloss": "Charisma"})

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository") as term_repo_cls, \
         patch("services.quiz_service.UserRepository"), \
         patch("services.quiz_service.UserService"):

        term_repo = term_repo_cls.return_value
        term_repo.get_wrong_answer_pool.return_value = ["Confidence", "Energy", "Vibe", "Style"]
        term_repo.get_terms_by_category.return_value = []

        service = QuizService()

        # Track that we see different option IDs (proving shuffling works)
        seen_option_ids = set()
        # Use term.meaning (what the code actually uses) instead of term.gloss
        normalized_correct = service._normalize_answer_text(term.meaning)

        # Run multiple times to catch shuffling issues and verify randomness
        for i in range(20):
            question, correct_option_id = service._format_multiple_choice(term, set())
            seen_option_ids.add(correct_option_id)

            # Find the option with the correct_option_id
            correct_option = None
            for opt in question.options:
                if opt.id == correct_option_id:
                    correct_option = opt
                    break

            # Verify we found the option
            assert correct_option is not None, \
                f"Could not find option with ID {correct_option_id}. " \
                f"Available IDs: {[opt.id for opt in question.options]}"

            # CRITICAL: Verify the option text matches the normalized correct answer
            assert correct_option.text == normalized_correct, \
                f"Option {correct_option_id} has text '{correct_option.text}' but should be '{normalized_correct}'. " \
                f"All options: {[(opt.id, opt.text) for opt in question.options]}"

            # Verify the correct answer text is actually in the options
            option_texts = [opt.text for opt in question.options]
            assert normalized_correct in option_texts, \
                f"Correct answer '{normalized_correct}' not found in options: {option_texts}"

        # Verify shuffling is actually working (we should see different IDs)
        # With 20 runs, we should see at least 2 different option IDs (statistically very likely)
        assert len(seen_option_ids) >= 2, \
            f"Shuffling may not be working - all correct_option_ids were the same: {seen_option_ids}. " \
            f"This suggests the correct answer is always at the same position after shuffling, which is a bug."


def test_get_next_question_raises_when_no_terms_available(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository") as term_repo_cls, \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        term_repo = term_repo_cls.return_value
        term_repo.get_wrong_answer_pool.return_value = ["wrong"] * 4
        term_repo.get_quiz_eligible_terms.return_value = []

        user_repo = user_repo_cls.return_value
        user_repo.get_daily_quiz_count.return_value = 0
        user_repo.get_active_quiz_session.return_value = QuizSessionRecord(
            session_id="existing",
            user_id="user-123",
            difficulty=QuizDifficulty.BEGINNER,
        )
        user_repo.get_quiz_stats.return_value = stats

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.PREMIUM)

        service = QuizService()

        with pytest.raises(ValidationError):
            service.get_next_question("user-123")


def test_submit_answer_updates_session_and_returns_response(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    term = _make_slang_term()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        correct_answers={"q1": "A"},
        term_names={"q1": term.term},
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository") as term_repo_cls, \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        term_repo = term_repo_cls.return_value
        term_repo.get_term_by_slang.return_value = term

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session
        user_repo.get_daily_quiz_count.return_value = 0
        user_repo.increment_daily_quiz_count.return_value = 1
        user_repo.get_daily_quiz_count.return_value = 0

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.PREMIUM)

        service = QuizService()
        response = service.submit_answer(
            "user-123",
            QuizAnswerRequest(
                session_id="session123",
                question_id="q1",
                selected_option="a",
                time_taken_seconds=4.5,
            ),
        )

    assert response.is_correct is True
    user_repo.update_quiz_session.assert_any_call(
        user_id="user-123",
        session_id="session123",
        questions_answered=1,
        correct_count=1,
        total_score=response.points_earned,
    )
    user_repo.increment_daily_quiz_count.assert_called_once_with("user-123")
    term_repo.update_quiz_statistics.assert_called_once_with(term.term, True)


def test_submit_answer_expires_stale_session(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    stale_session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        correct_answers={"q1": "a"},
        term_names={"q1": "rizz"},
        last_activity=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = stale_session
        user_repo.get_daily_quiz_count.return_value = 0

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.PREMIUM)

        service = QuizService()

        with pytest.raises(ValidationError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=1.0,
                ),
            )

    user_repo.update_quiz_session.assert_called_with(
        user_id="user-123",
        session_id="session123",
        status="expired",
    )


def test_submit_answer_validates_question_presence(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        correct_answers={},
        term_names={},
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session
        user_repo.get_daily_quiz_count.return_value = 0

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.PREMIUM)

        service = QuizService()

        with pytest.raises(ValidationError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="missing-question",
                    selected_option="a",
                    time_taken_seconds=2.0,
                ),
            )


def test_submit_answer_validates_session_presence(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = None

        service = QuizService()

        with pytest.raises(ValidationError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=2.0,
                ),
            )


def test_submit_answer_validates_session_owner(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="someone-else",
        difficulty=QuizDifficulty.BEGINNER,
        correct_answers={"q1": "a"},
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()

        with pytest.raises(ValidationError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=1.0,
                ),
            )


def test_submit_answer_requires_active_status(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        status=QuizSessionStatus.COMPLETED,
        correct_answers={"q1": "a"},
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()

        with pytest.raises(ValidationError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=1.0,
                ),
            )


def test_submit_answer_enforces_free_limit(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        questions_answered=3,
        correct_count=2,
        total_score=20.0,
        correct_answers={"q1": "a"},
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session
        user_repo.get_daily_quiz_count.return_value = dummy_config.get_config(QuizConfig).free_daily_limit

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.FREE)

        service = QuizService()

        with pytest.raises(UsageLimitExceededError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=1.0,
                ),
            )

        # Session should be finalized when limit is reached
        user_repo.finalize_quiz_session.assert_called_once_with(
            user_id="user-123",
            session_id="session123",
            questions_answered=3,
            correct_count=2,
            total_score=20.0,
            total_possible=30.0,
        )


def test_submit_answer_does_not_finalize_empty_session_on_limit(stats: QuizStats) -> None:
    """Test that session is not finalized if no questions have been answered."""
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        questions_answered=0,  # No questions answered
        correct_count=0,
        total_score=0.0,
        correct_answers={},
        last_activity=datetime.now(timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService") as user_service_cls:

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session
        user_repo.get_daily_quiz_count.return_value = dummy_config.get_config(QuizConfig).free_daily_limit

        user_service = user_service_cls.return_value
        user_service.get_user.return_value = Mock(tier=UserTier.FREE)

        service = QuizService()

        with pytest.raises(UsageLimitExceededError):
            service.submit_answer(
                "user-123",
                QuizAnswerRequest(
                    session_id="session123",
                    question_id="q1",
                    selected_option="a",
                    time_taken_seconds=1.0,
                ),
            )

        # Session should NOT be finalized if no questions answered
        user_repo.finalize_quiz_session.assert_not_called()


def test_get_session_progress_returns_metrics(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        questions_answered=4,
        correct_count=3,
        total_score=25.0,
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()
        progress = service.get_session_progress("user-123", "session123")

    assert isinstance(progress, QuizSessionProgress)
    assert progress.questions_answered == 4
    assert progress.correct_count == 3
    user_repo.get_quiz_session.assert_called_with("user-123", "session123")


def test_get_session_progress_validates_user(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="different",
        difficulty=QuizDifficulty.BEGINNER,
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()

        with pytest.raises(ValidationError):
            service.get_session_progress("user-123", "session123")


def test_end_session_finalizes_and_returns_result(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        questions_answered=3,
        correct_count=2,
        total_score=24.0,
        term_names={"q1": "rizz"},
        correct_answers={"q1": "a"},
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()
        result = service.end_session("user-123", "session123")

    assert result.total_questions == 3
    user_repo.finalize_quiz_session.assert_called_once()


def test_end_session_validates_state(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    base_session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = None
        service = QuizService()
        with pytest.raises(ValidationError):
            service.end_session("user-123", "session123")

        # Session belongs to another user
        wrong_owner = base_session.model_copy(update={"user_id": "other"})
        user_repo.get_quiz_session.return_value = wrong_owner
        with pytest.raises(ValidationError):
            service.end_session("user-123", "session123")

        # Session already completed
        completed = base_session.model_copy(update={"status": QuizSessionStatus.COMPLETED, "questions_answered": 1})
        user_repo.get_quiz_session.return_value = completed
        with pytest.raises(ValidationError):
            service.end_session("user-123", "session123")

        # Session without answered questions
        incomplete = base_session.model_copy(update={"status": QuizSessionStatus.ACTIVE})
        user_repo.get_quiz_session.return_value = incomplete
        with pytest.raises(ValidationError):
            service.end_session("user-123", "session123")


def test_end_session_parses_string_dates(stats: QuizStats) -> None:
    dummy_config = DummyQuizConfigService()
    session = QuizSessionRecord(
        session_id="session123",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        status=QuizSessionStatus.ACTIVE,
        questions_answered=2,
        correct_count=1,
        total_score=12.0,
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
    )

    with patch("services.quiz_service.get_config_service", return_value=dummy_config), \
         patch("services.quiz_service.LexiconRepository"), \
         patch("services.quiz_service.UserRepository") as user_repo_cls, \
         patch("services.quiz_service.UserService"):

        user_repo = user_repo_cls.return_value
        user_repo.get_quiz_session.return_value = session

        service = QuizService()
        service.end_session("user-123", "session123")

    user_repo.finalize_quiz_session.assert_called_once()


def test_check_quiz_eligibility_includes_active_session_stats(stats: QuizStats) -> None:
    """Test that quiz eligibility includes stats from active session."""
    active_session = QuizSessionRecord(
        session_id="active-session",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        status=QuizSessionStatus.ACTIVE,
        questions_answered=5,
        correct_count=4,
        total_score=35.0,
        correct_answers={"q1": "a", "q2": "b", "q3": "c", "q4": "d", "q5": "a"},
        term_names={"q1": "bussin", "q2": "cap", "q3": "fire", "q4": "slay", "q5": "bet"},
        used_wrong_options=[],
        started_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    service, user_repo, _ = _build_service(
        UserTier.FREE, quizzes_today=1, quiz_stats=stats, active_session=active_session
    )

    result = service.check_quiz_eligibility("user-123")

    # Should include active session stats
    assert result.total_quizzes == 10  # Only completed quizzes count
    assert result.total_questions == 55  # 50 finalized + 5 from active session
    assert result.total_correct == 44  # 40 finalized + 4 from active session
    assert result.accuracy_rate == pytest.approx(0.8, abs=0.01)  # 44/55 = 0.8
    assert result.average_score == 7.5  # Only finalized quizzes
    # Active session score: 35/50 = 70%, best was 10.0%, so best_score should update to 70.0
    assert result.best_score == 70.0
    user_repo.get_active_quiz_session.assert_called_once_with("user-123")


def test_check_quiz_eligibility_updates_best_score_with_active_session(stats: QuizStats) -> None:
    """Test that quiz eligibility updates best_score if active session is better."""
    # Finalized stats with lower best score
    lower_stats = QuizStats(
        total_quizzes=1,
        average_score=7.0,
        best_score=7.0,
        total_correct=7,
        total_questions=10,
        accuracy_rate=0.70,
    )

    # Active session with better score (90%)
    active_session = QuizSessionRecord(
        session_id="active-session",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        status=QuizSessionStatus.ACTIVE,
        questions_answered=10,
        correct_count=9,
        total_score=90.0,  # 90/100 = 90%
        correct_answers={f"q{i}": "a" for i in range(1, 11)},
        term_names={f"q{i}": f"term{i}" for i in range(1, 11)},
        used_wrong_options=[],
        started_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    service, user_repo, _ = _build_service(
        UserTier.FREE, quizzes_today=1, quiz_stats=lower_stats, active_session=active_session
    )

    result = service.check_quiz_eligibility("user-123")

    # Best score should be updated to active session's 90%
    assert result.best_score == 90.0
    assert result.total_questions == 20  # 10 finalized + 10 from active session
    assert result.total_correct == 16  # 7 finalized + 9 from active session


def test_check_quiz_eligibility_ignores_active_session_with_no_questions(stats: QuizStats) -> None:
    """Test that quiz eligibility ignores active session with no questions answered."""
    # Active session with no questions answered yet
    active_session = QuizSessionRecord(
        session_id="active-session",
        user_id="user-123",
        difficulty=QuizDifficulty.BEGINNER,
        status=QuizSessionStatus.ACTIVE,
        questions_answered=0,  # No questions answered yet
        correct_count=0,
        total_score=0.0,
        correct_answers={},
        term_names={},
        used_wrong_options=[],
        started_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    service, user_repo, _ = _build_service(
        UserTier.FREE, quizzes_today=1, quiz_stats=stats, active_session=active_session
    )

    result = service.check_quiz_eligibility("user-123")

    # Should use only finalized stats (active session has no progress)
    assert result.total_questions == 50
    assert result.total_correct == 40
    assert result.accuracy_rate == 0.8
    assert result.best_score == 10.0
