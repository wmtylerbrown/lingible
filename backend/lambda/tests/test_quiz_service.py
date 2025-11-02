"""Tests for QuizService."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from src.models.quiz import (
    QuizDifficulty,
    QuizQuestionResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizSessionProgress,
    QuizCategory,
)
from src.models.users import UserTier
from src.utils.exceptions import ValidationError, UsageLimitExceededError


class TestQuizService:
    """Test QuizService functionality."""

    @pytest.fixture
    def mock_quiz_service(self):
        """Create mocked QuizService."""
        with patch('services.quiz_service.SlangTermRepository') as mock_repo_class:
            with patch('services.quiz_service.UserRepository') as mock_user_repo_class:
                with patch('services.quiz_service.UserService') as mock_user_service_class:
                    with patch('services.quiz_service.get_config_service') as mock_config:
                        # Setup config mock
                        mock_config_service = Mock()
                        mock_quiz_config = Mock()
                        mock_quiz_config.free_daily_limit = 3
                        mock_quiz_config.points_per_correct = 10
                        mock_quiz_config.enable_time_bonus = True
                        mock_quiz_config.time_limit_seconds = 60
                        mock_config_service.get_config.return_value = mock_quiz_config
                        mock_config.return_value = mock_config_service

                        # Setup repository mock
                        mock_repo = Mock()
                        mock_repo_class.return_value = mock_repo

                        # Setup user repository mock
                        mock_user_repo = Mock()
                        mock_user_repo_class.return_value = mock_user_repo

                        # Setup user service mock
                        mock_user_service = Mock()
                        mock_user_service_class.return_value = mock_user_service

                        # Mock wrong answer pools for all categories
                        from models.quiz import QuizCategory

                        def mock_get_pool(category: str):
                            """Return mock pool for any category."""
                            return ["Bad", "Okay", "Average", "Terrible", "Awful", "Good", "Great", "Perfect"]

                        mock_repo.get_wrong_answer_pool = mock_get_pool

                        # Reset pool state for fresh test run
                        from services.quiz_service import QuizService
                        QuizService._wrong_answer_pools = {}
                        QuizService._pools_loaded = False

                        service = QuizService()
                        service.repository = mock_repo
                        service.user_repository = mock_user_repo
                        service.user_service = mock_user_service
                        return service

    @pytest.fixture
    def premium_user_profile(self):
        """Premium user profile."""
        profile = Mock()
        profile.tier = UserTier.PREMIUM
        return profile

    @pytest.fixture
    def free_user_profile(self):
        """Free user profile."""
        profile = Mock()
        profile.tier = UserTier.FREE
        return profile

    @pytest.fixture
    def sample_quiz_terms(self):
        """Sample quiz-eligible terms."""
        return [
            {
                "slang_term": "bussin",
                "meaning": "Really good",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
                "quiz_category": "approval",
                "example_usage": "That pizza was bussin!",
            },
            {
                "slang_term": "cap",
                "meaning": "Lie",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
                "quiz_category": "disapproval",
                "example_usage": "That's cap!",
            }
        ]

    def test_check_quiz_eligibility_premium_unlimited(self, mock_quiz_service, premium_user_profile):
        """Test premium users can take unlimited quizzes."""
        mock_quiz_service.user_service.get_user.return_value = premium_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 5  # Over free limit
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {
            "total_quizzes": 10,
            "average_score": 85.0,
            "best_score": 100,
            "total_correct": 85,
            "total_questions": 100,
            "accuracy_rate": 0.85,
        }

        result = mock_quiz_service.check_quiz_eligibility("user_123")

        assert result.can_take_quiz is True
        assert result.quizzes_today == 5
        assert result.total_quizzes == 10

    def test_check_quiz_eligibility_free_within_limit(self, mock_quiz_service, free_user_profile):
        """Test free users within daily limit can take quizzes."""
        mock_quiz_service.user_service.get_user.return_value = free_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 2  # Under limit of 3
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {
            "total_quizzes": 5,
            "average_score": 75.0,
            "best_score": 90,
            "total_correct": 38,
            "total_questions": 50,
            "accuracy_rate": 0.76,
        }

        result = mock_quiz_service.check_quiz_eligibility("user_123")

        assert result.can_take_quiz is True
        assert result.quizzes_today == 2
        assert result.reason is None or "limit" not in result.reason.lower()

    def test_check_quiz_eligibility_free_over_limit(self, mock_quiz_service, free_user_profile):
        """Test free users over daily limit cannot take quizzes."""
        mock_quiz_service.user_service.get_user.return_value = free_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 3  # At limit
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {
            "total_quizzes": 8,
            "average_score": 80.0,
            "best_score": 95,
            "total_correct": 40,
            "total_questions": 50,
            "accuracy_rate": 0.80,
        }

        result = mock_quiz_service.check_quiz_eligibility("user_123")

        assert result.can_take_quiz is False
        assert "limit" in result.reason.lower()
        assert "upgrade" in result.reason.lower()

    def test_format_multiple_choice_question(self, mock_quiz_service, sample_quiz_terms):
        """Test formatting term as multiple choice question."""
        term = sample_quiz_terms[0]  # "bussin"

        question, correct_option = mock_quiz_service._format_multiple_choice(term, set())

        assert question.slang_term == "bussin"
        assert question.question_text == "What does 'bussin' mean?"
        assert len(question.options) == 4
        assert correct_option in ["a", "b", "c", "d"]

        # Verify correct answer is in options
        option_texts = [opt.text for opt in question.options]
        assert "Really good" in option_texts

    def test_generate_wrong_options_with_existing(self, mock_quiz_service):
        """Test wrong option generation with existing options."""
        term = {
            "quiz_category": "approval",
            "slang_term": "bussin",
            "meaning": "Really good",
        }
        existing = ["Bad", "Okay"]

        result = mock_quiz_service._generate_wrong_options(term, set(existing), existing=existing)

        assert len(result) == 3
        assert "Bad" in result
        assert "Okay" in result
        assert "Really good" not in result

    def test_generate_wrong_options_without_existing(self, mock_quiz_service):
        """Test wrong option generation without existing options."""
        term = {
            "quiz_category": "approval",
            "slang_term": "bussin",
            "meaning": "Really good",
        }

        result = mock_quiz_service._generate_wrong_options(term, set(), existing=[])

        assert len(result) == 3
        assert "Really good" not in result
        # Should include generic options
        assert any(opt in result for opt in ["Bad", "Okay", "Average"])

    # ===== Stateless API Tests =====

    def test_get_next_question_creates_session(self, mock_quiz_service, premium_user_profile, sample_quiz_terms):
        """Test get_next_question creates new session when none exists."""
        mock_quiz_service.user_service.get_user.return_value = premium_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_active_quiz_session.return_value = None  # No active session
        mock_quiz_service.repository.create_quiz_session.return_value = True
        mock_quiz_service.repository.get_quiz_session.return_value = {
            "session_id": "session_123",
            "user_id": "user_123",
            "difficulty": "beginner",
            "questions_answered": 0,
            "correct_count": 0,
            "total_score": 0.0,
            "correct_answers": {},
            "term_names": {},
            "used_wrong_options": [],
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_quiz_service.repository.get_quiz_eligible_terms.return_value = sample_quiz_terms
        mock_quiz_service.repository.update_quiz_session.return_value = True

        response = mock_quiz_service.get_next_question("user_123", QuizDifficulty.BEGINNER)

        assert isinstance(response, QuizQuestionResponse)
        assert response.session_id == "session_123"
        assert response.question.slang_term in ["bussin", "cap"]
        assert len(response.question.options) == 4
        mock_quiz_service.repository.create_quiz_session.assert_called_once()

    def test_get_next_question_uses_existing_session(self, mock_quiz_service, premium_user_profile, sample_quiz_terms):
        """Test get_next_question uses existing active session."""
        existing_session = {
            "session_id": "session_456",
            "user_id": "user_123",
            "difficulty": "beginner",
            "questions_answered": 1,
            "correct_count": 1,
            "total_score": 8.5,
            "correct_answers": {"q1": "a"},
            "term_names": {"q1": "bussin"},
            "used_wrong_options": ["Bad", "Okay", "Average"],
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_quiz_service.user_service.get_user.return_value = premium_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_active_quiz_session.return_value = existing_session
        mock_quiz_service.repository.get_quiz_eligible_terms.return_value = sample_quiz_terms
        mock_quiz_service.repository.update_quiz_session.return_value = True

        response = mock_quiz_service.get_next_question("user_123", QuizDifficulty.BEGINNER)

        assert response.session_id == "session_456"
        mock_quiz_service.repository.create_quiz_session.assert_not_called()

    def test_get_next_question_excludes_used_terms(self, mock_quiz_service, premium_user_profile):
        """Test get_next_question excludes terms that have already been used in the session."""
        # Session with "bussin" already used
        existing_session = {
            "session_id": "session_789",
            "user_id": "user_123",
            "difficulty": "beginner",
            "questions_answered": 2,
            "correct_count": 2,
            "total_score": 17.0,
            "correct_answers": {"q1": "a", "q2": "b"},
            "term_names": {"q1": "bussin", "q2": "cap"},  # Both terms already used
            "used_wrong_options": ["Bad", "Okay", "Average"],
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        # Available terms include the already-used ones plus new ones
        available_terms = [
            {
                "slang_term": "bussin",  # Already used
                "meaning": "Really good",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
            },
            {
                "slang_term": "cap",  # Already used
                "meaning": "Lie",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
            },
            {
                "slang_term": "slay",  # NEW - not used yet
                "meaning": "Do something exceptionally well",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
            },
            {
                "slang_term": "fire",  # NEW - not used yet
                "meaning": "Amazing",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
            },
        ]

        mock_quiz_service.user_service.get_user.return_value = premium_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_active_quiz_session.return_value = existing_session

        # Mock get_quiz_eligible_terms to return terms excluding the used ones
        def mock_get_terms(difficulty, limit, exclude_terms):
            """Mock that filters out excluded terms."""
            excluded_set = set(exclude_terms) if exclude_terms else set()
            filtered = [t for t in available_terms if t["slang_term"] not in excluded_set]
            return filtered[:limit]

        mock_quiz_service.repository.get_quiz_eligible_terms.side_effect = mock_get_terms
        mock_quiz_service.repository.update_quiz_session.return_value = True

        response = mock_quiz_service.get_next_question("user_123", QuizDifficulty.BEGINNER)

        # Verify the term used is NOT one of the already-used terms
        assert response.question.slang_term not in ["bussin", "cap"]
        assert response.question.slang_term in ["slay", "fire"]

        # Verify get_quiz_eligible_terms was called with exclude_terms
        call_args = mock_quiz_service.repository.get_quiz_eligible_terms.call_args
        assert call_args is not None
        assert "exclude_terms" in call_args.kwargs or len(call_args.kwargs.get("exclude_terms", [])) > 0
        excluded_terms = call_args.kwargs.get("exclude_terms", [])
        assert "bussin" in excluded_terms
        assert "cap" in excluded_terms

    def test_get_next_question_handles_all_terms_exhausted(self, mock_quiz_service, premium_user_profile):
        """Test get_next_question raises error when all available terms are exhausted."""
        # Session that has used all available terms
        existing_session = {
            "session_id": "session_exhausted",
            "user_id": "user_123",
            "difficulty": "beginner",
            "questions_answered": 2,
            "correct_count": 2,
            "total_score": 17.0,
            "correct_answers": {"q1": "a", "q2": "b"},
            "term_names": {"q1": "bussin", "q2": "cap"},
            "used_wrong_options": [],
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        # Only 2 terms available (both already used)
        available_terms = [
            {"slang_term": "bussin", "meaning": "Really good", "is_quiz_eligible": True},
            {"slang_term": "cap", "meaning": "Lie", "is_quiz_eligible": True},
        ]

        mock_quiz_service.user_service.get_user.return_value = premium_user_profile
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_active_quiz_session.return_value = existing_session

        def mock_get_terms(difficulty, limit, exclude_terms):
            """Mock that filters out excluded terms."""
            excluded_set = set(exclude_terms) if exclude_terms else set()
            filtered = [t for t in available_terms if t["slang_term"] not in excluded_set]
            return filtered[:limit]

        mock_quiz_service.repository.get_quiz_eligible_terms.side_effect = mock_get_terms

        # Should raise ValidationError when no terms available
        with pytest.raises(ValidationError) as exc_info:
            mock_quiz_service.get_next_question("user_123", QuizDifficulty.BEGINNER)

        # Verify the error message
        assert "Not enough terms available" in exc_info.value.message

    def test_get_next_question_free_tier_limit(self, mock_quiz_service, free_user_profile):
        """Test get_next_question respects free tier daily limit."""
        from datetime import datetime, timezone
        mock_quiz_service.user_service.get_user.return_value = free_user_profile
        today = datetime.now(timezone.utc).date().isoformat()
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 3  # At limit

        with pytest.raises(UsageLimitExceededError) as exc_info:
            mock_quiz_service.get_next_question("user_123", QuizDifficulty.BEGINNER)

        error = exc_info.value
        assert error.details["limit_type"] == "quiz_questions"
        assert error.details["current_usage"] == 3
        assert error.details["limit"] == 3
        assert "Daily limit" in error.message

    def test_submit_answer_correct(self, mock_quiz_service, sample_quiz_terms):
        """Test submit_answer with correct answer."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 0,
            "correct_count": 0,
            "total_score": 0.0,
            "correct_answers": {"q1": "a"},
            "term_names": {"q1": "bussin"},
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session
        mock_quiz_service.repository.get_term_by_slang.return_value = {"meaning": "Really good"}
        mock_quiz_service.repository.update_quiz_session.return_value = True
        mock_quiz_service.user_repository.increment_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.update_quiz_statistics.return_value = None

        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="a",
            time_taken_seconds=5.0
        )

        response = mock_quiz_service.submit_answer("user_123", answer_request)

        assert isinstance(response, QuizAnswerResponse)
        assert response.is_correct is True
        assert response.points_earned > 0
        assert response.running_stats.questions_answered == 1
        assert response.running_stats.correct_count == 1
        mock_quiz_service.repository.update_quiz_statistics.assert_called_once_with("bussin", True)

    def test_submit_answer_incorrect(self, mock_quiz_service):
        """Test submit_answer with incorrect answer."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 0,
            "correct_count": 0,
            "total_score": 0.0,
            "correct_answers": {"q1": "a"},
            "term_names": {"q1": "bussin"},
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session
        mock_quiz_service.repository.get_term_by_slang.return_value = {"meaning": "Really good"}
        mock_quiz_service.repository.update_quiz_session.return_value = True
        mock_quiz_service.user_repository.increment_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.update_quiz_statistics.return_value = None

        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="b",  # Wrong answer
            time_taken_seconds=10.0
        )

        response = mock_quiz_service.submit_answer("user_123", answer_request)

        assert response.is_correct is False
        assert response.points_earned == 0.0
        assert response.running_stats.correct_count == 0
        mock_quiz_service.repository.update_quiz_statistics.assert_called_once_with("bussin", False)

    def test_submit_answer_expired_session(self, mock_quiz_service):
        """Test submit_answer with expired session."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "status": "active",
            "last_activity": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),  # Expired
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session
        mock_quiz_service.repository.update_quiz_session.return_value = True

        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="a",
            time_taken_seconds=5.0
        )

        with pytest.raises(ValidationError, match="expired"):
            mock_quiz_service.submit_answer("user_123", answer_request)

    def test_get_session_progress(self, mock_quiz_service):
        """Test get_session_progress returns current stats."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 5,
            "correct_count": 4,
            "total_score": 35.5,
            "started_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session

        progress = mock_quiz_service.get_session_progress("user_123", "session_123")

        assert isinstance(progress, QuizSessionProgress)
        assert progress.questions_answered == 5
        assert progress.correct_count == 4
        assert progress.total_score == 35.5
        assert progress.accuracy == 0.8  # 4/5
        assert progress.time_spent_seconds > 0

    def test_end_session(self, mock_quiz_service):
        """Test end_session saves results and marks session complete."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 5,
            "correct_count": 4,
            "total_score": 35.5,
            "difficulty": "beginner",
            "status": "active",
            "started_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session
        mock_quiz_service.repository.update_quiz_session.return_value = True
        mock_quiz_service.repository.save_quiz_result.return_value = True

        result = mock_quiz_service.end_session("user_123", "session_123")

        assert result.session_id == "session_123"
        assert result.score == 35.5
        assert result.correct_count == 4
        assert result.total_questions == 5
        mock_quiz_service.repository.save_quiz_result.assert_called_once()
        # Verify session marked as completed
        mock_quiz_service.repository.update_quiz_session.assert_any_call(
            session_id="session_123",
            status="completed"
        )

    def test_end_session_no_questions(self, mock_quiz_service):
        """Test end_session fails if no questions answered."""
        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 0,
            "status": "active",
        }

        mock_quiz_service.repository.get_quiz_session.return_value = session

        with pytest.raises(ValidationError, match="no questions answered"):
            mock_quiz_service.end_session("user_123", "session_123")

    def test_answer_normalization(self, mock_quiz_service):
        """Test answer normalization extracts first meaning and standardizes formatting."""
        # Test semicolon separation - should extract first part only
        assert mock_quiz_service._normalize_answer_text("Too long;didn't read") == "Too long"
        assert mock_quiz_service._normalize_answer_text("Really good; awesome; amazing") == "Really good"
        assert mock_quiz_service._normalize_answer_text("Really good; awesome") == "Really good"

        # Test capitalization - sentence case
        assert mock_quiz_service._normalize_answer_text("really good") == "Really good"
        assert mock_quiz_service._normalize_answer_text("REALLY GOOD") == "Really good"
        assert mock_quiz_service._normalize_answer_text("Really Good") == "Really good"
        assert mock_quiz_service._normalize_answer_text("r") == "R"
        assert mock_quiz_service._normalize_answer_text("") == ""

        # Test no semicolon - just capitalization
        assert mock_quiz_service._normalize_answer_text("really awesome") == "Really awesome"

    def test_per_question_scoring_fast_answer(self, mock_quiz_service):
        """Test per-question scoring with fast answer."""
        # Fast answer (5 seconds out of 30)
        points = mock_quiz_service._calculate_question_points(is_correct=True, time_taken_seconds=5.0)
        # Should be high points (close to max of 10)
        assert points > 8.0
        assert points <= 10.0

    def test_per_question_scoring_slow_answer(self, mock_quiz_service):
        """Test per-question scoring with slow answer."""
        # Slow answer (25 seconds out of 30)
        points = mock_quiz_service._calculate_question_points(is_correct=True, time_taken_seconds=25.0)
        # Should be lower points but still above minimum
        assert points > 1.0
        assert points < 5.0

    def test_per_question_scoring_incorrect(self, mock_quiz_service):
        """Test per-question scoring returns 0 for incorrect answers."""
        points = mock_quiz_service._calculate_question_points(is_correct=False, time_taken_seconds=5.0)
        assert points == 0.0

    def test_per_question_scoring_minimum_points(self, mock_quiz_service):
        """Test per-question scoring ensures minimum 1 point."""
        # Very slow answer (30+ seconds)
        points = mock_quiz_service._calculate_question_points(is_correct=True, time_taken_seconds=35.0)
        # Should still give minimum 1 point
        assert points >= 1.0

    def test_format_multiple_choice_normalizes_answers(self, mock_quiz_service):
        """Test that _format_multiple_choice normalizes all options."""
        term = {
            "slang_term": "test",
            "meaning": "really good; awesome",  # Has semicolon, lowercase
            "quiz_category": "approval",
        }

        question, correct_option = mock_quiz_service._format_multiple_choice(term, set())

        # All options should be normalized
        for option in question.options:
            # Should not contain semicolon (first part extracted)
            assert ";" not in option.text
            # First letter should be uppercase (sentence case)
            assert option.text[0].isupper()
            # Rest should be lowercase
            if len(option.text) > 1:
                assert option.text[1:].islower() or option.text[1:] == ""

    def test_generate_wrong_options_avoids_duplicates(self, mock_quiz_service):
        """Test that wrong options avoid duplicates and correct answer."""
        term = {
            "slang_term": "test",
            "meaning": "Really good",
            "quiz_category": "approval",
        }
        used_options = {"Bad", "Okay"}

        result = mock_quiz_service._generate_wrong_options(term, used_options, existing=[])

        assert len(result) == 3
        assert "Really good" not in result  # Should not include correct answer
        # Should not include already used options (if normalized)
        normalized_used = {mock_quiz_service._normalize_answer_text(opt) for opt in used_options}
        normalized_result = [mock_quiz_service._normalize_answer_text(opt) for opt in result]
        for opt in normalized_used:
            assert opt not in normalized_result

    def test_ensure_pools_loaded_success(self, mock_quiz_service):
        """Test that pool loading succeeds and doesn't raise exceptions."""
        from services.quiz_service import QuizService

        # Reset state
        QuizService._wrong_answer_pools = {}
        QuizService._pools_loaded = False

        # Mock repository to return pools
        mock_pool = ["Bad", "Okay", "Average", "Terrible", "Awful"]
        mock_quiz_service.repository.get_wrong_answer_pool.return_value = mock_pool

        # This should not raise an exception
        mock_quiz_service._ensure_pools_loaded()

        # Verify pools were loaded for all categories
        assert QuizService._pools_loaded is True
        assert len(QuizService._wrong_answer_pools) == len(QuizCategory)

        # Verify each category has a pool
        for category in QuizCategory:
            assert category.value in QuizService._wrong_answer_pools
            assert len(QuizService._wrong_answer_pools[category.value]) == len(mock_pool)

    def test_ensure_pools_loaded_handles_missing_pools(self, mock_quiz_service):
        """Test that pool loading handles missing pools gracefully."""
        from services.quiz_service import QuizService

        # Reset state
        QuizService._wrong_answer_pools = {}
        QuizService._pools_loaded = False

        # Mock repository to return None (pool not found)
        mock_quiz_service.repository.get_wrong_answer_pool.return_value = None

        # This should not raise an exception, should use empty pools
        mock_quiz_service._ensure_pools_loaded()

        # Verify pools_loaded is True even with empty pools
        assert QuizService._pools_loaded is True
        # Should have entries for all categories, even if empty
        assert len(QuizService._wrong_answer_pools) == len(QuizCategory)

    def test_submit_answer_free_tier_limit_exceeded(self, mock_quiz_service, free_user_profile):
        """Test submit_answer raises UsageLimitExceededError when free tier limit is exceeded."""
        from datetime import datetime, timezone

        session = {
            "session_id": "session_123",
            "user_id": "user_123",
            "questions_answered": 0,
            "correct_count": 0,
            "total_score": 0.0,
            "correct_answers": {"q1": "a"},
            "term_names": {"q1": "bussin"},
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        mock_quiz_service.user_service.get_user.return_value = free_user_profile
        mock_quiz_service.repository.get_quiz_session.return_value = session
        today = datetime.now(timezone.utc).date().isoformat()
        mock_quiz_service.user_repository.get_daily_quiz_count.return_value = 3  # At limit

        answer_request = QuizAnswerRequest(
            session_id="session_123",
            question_id="q1",
            selected_option="a",
            time_taken_seconds=5.0
        )

        with pytest.raises(UsageLimitExceededError) as exc_info:
            mock_quiz_service.submit_answer("user_123", answer_request)

        error = exc_info.value
        assert error.details["limit_type"] == "quiz_questions"
        assert error.details["current_usage"] == 3
        assert error.details["limit"] == 3
        assert "Daily limit" in error.message
