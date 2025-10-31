"""Tests for QuizService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from models.quiz import (
    QuizChallengeRequest,
    QuizSubmissionRequest,
    QuizAnswer,
    QuizDifficulty,
    ChallengeType,
)
from models.users import UserTier
from utils.exceptions import ValidationError, InsufficientPermissionsError


class TestQuizService:
    """Test QuizService functionality."""

    @pytest.fixture
    def mock_quiz_service(self):
        """Create mocked QuizService."""
        with patch('services.quiz_service.SlangTermRepository') as mock_repo_class:
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

                    # Setup user service mock
                    mock_user_service = Mock()
                    mock_user_service_class.return_value = mock_user_service

                    from services.quiz_service import QuizService
                    service = QuizService()
                    service.repository = mock_repo
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
                "quiz_wrong_options": ["Bad", "Okay", "Average"],
                "example_usage": "That pizza was bussin!",
            },
            {
                "slang_term": "cap",
                "meaning": "Lie",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
                "quiz_category": "disapproval",
                "quiz_wrong_options": ["Truth", "Fact", "Real"],
                "example_usage": "That's cap!",
            }
        ]

    def test_check_quiz_eligibility_premium_unlimited(self, mock_quiz_service, premium_user_profile):
        """Test premium users can take unlimited quizzes."""
        mock_quiz_service.user_service.get_user_profile.return_value = premium_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 5  # Over free limit
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
        mock_quiz_service.user_service.get_user_profile.return_value = free_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 2  # Under limit of 3
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
        assert "limit" not in result.reason.lower()

    def test_check_quiz_eligibility_free_over_limit(self, mock_quiz_service, free_user_profile):
        """Test free users over daily limit cannot take quizzes."""
        mock_quiz_service.user_service.get_user_profile.return_value = free_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 3  # At limit
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

    def test_generate_challenge_success(self, mock_quiz_service, premium_user_profile, sample_quiz_terms):
        """Test successful challenge generation."""
        mock_quiz_service.user_service.get_user_profile.return_value = premium_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {"total_quizzes": 5}
        mock_quiz_service.repository.get_quiz_eligible_terms.return_value = sample_quiz_terms

        request = QuizChallengeRequest(
            difficulty=QuizDifficulty.BEGINNER,
            challenge_type=ChallengeType.MULTIPLE_CHOICE,
            question_count=2
        )

        result = mock_quiz_service.generate_challenge("user_123", request)

        assert result.challenge_id.startswith("quiz_")
        assert len(result.questions) == 2
        assert result.difficulty == QuizDifficulty.BEGINNER
        assert result.challenge_type == ChallengeType.MULTIPLE_CHOICE
        assert result.time_limit_seconds == 60

    def test_generate_challenge_insufficient_terms(self, mock_quiz_service, premium_user_profile):
        """Test challenge generation fails when insufficient terms available."""
        mock_quiz_service.user_service.get_user_profile.return_value = premium_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 1
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {"total_quizzes": 5}
        mock_quiz_service.repository.get_quiz_eligible_terms.return_value = []  # No terms

        request = QuizChallengeRequest(
            difficulty=QuizDifficulty.BEGINNER,
            challenge_type=ChallengeType.MULTIPLE_CHOICE,
            question_count=10
        )

        with pytest.raises(ValidationError, match="Not enough terms available"):
            mock_quiz_service.generate_challenge("user_123", request)

    def test_generate_challenge_not_eligible(self, mock_quiz_service, free_user_profile):
        """Test challenge generation fails when user not eligible."""
        mock_quiz_service.user_service.get_user_profile.return_value = free_user_profile
        mock_quiz_service.repository.get_daily_quiz_count.return_value = 5  # Over limit
        mock_quiz_service.repository.get_user_quiz_stats.return_value = {"total_quizzes": 10}

        request = QuizChallengeRequest(
            difficulty=QuizDifficulty.BEGINNER,
            challenge_type=ChallengeType.MULTIPLE_CHOICE,
            question_count=10
        )

        with pytest.raises(InsufficientPermissionsError):
            mock_quiz_service.generate_challenge("user_123", request)

    def test_format_multiple_choice_question(self, mock_quiz_service, sample_quiz_terms):
        """Test formatting term as multiple choice question."""
        term = sample_quiz_terms[0]  # "bussin"

        question, correct_option = mock_quiz_service._format_multiple_choice(term)

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

        result = mock_quiz_service._generate_wrong_options(term, existing)

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

        result = mock_quiz_service._generate_wrong_options(term)

        assert len(result) == 3
        assert "Really good" not in result
        # Should include generic options
        assert any(opt in result for opt in ["Bad", "Okay", "Average"])

    def test_submit_quiz_success(self, mock_quiz_service):
        """Test successful quiz submission."""
        challenge_id = "quiz_123"
        user_id = "user_456"

        # Mock active challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": {"q1": "a", "q2": "b"},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {"q1": "bussin", "q2": "cap"},
            "difficulty": "beginner"
        }

        # Mock repository methods
        mock_quiz_service.repository.save_quiz_result.return_value = True
        mock_quiz_service.repository.increment_daily_quiz_count.return_value = 2
        mock_quiz_service.repository.get_term_by_slang.side_effect = [
            {"meaning": "Really good"},
            {"meaning": "Lie"}
        ]

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[
                QuizAnswer(question_id="q1", selected="a"),
                QuizAnswer(question_id="q2", selected="b")
            ],
            time_taken_seconds=45
        )

        result = mock_quiz_service.submit_quiz(user_id, submission)

        assert result.challenge_id == challenge_id
        assert result.correct_count == 2
        assert result.total_questions == 2
        assert result.score == 20  # 2 correct * 10 points + time bonus
        assert len(result.results) == 2
        assert result.results[0].is_correct is True

    def test_submit_quiz_invalid_challenge(self, mock_quiz_service):
        """Test quiz submission with invalid challenge ID."""
        submission = QuizSubmissionRequest(
            challenge_id="invalid_challenge",
            answers=[],
            time_taken_seconds=45
        )

        with pytest.raises(ValidationError, match="Invalid or expired challenge"):
            mock_quiz_service.submit_quiz("user_123", submission)

    def test_submit_quiz_wrong_user(self, mock_quiz_service):
        """Test quiz submission with wrong user."""
        challenge_id = "quiz_123"

        # Mock active challenge for different user
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": "other_user",
            "correct_answers": {},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {},
            "difficulty": "beginner"
        }

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[],
            time_taken_seconds=45
        )

        with pytest.raises(ValidationError, match="does not belong to this user"):
            mock_quiz_service.submit_quiz("user_123", submission)

    def test_submit_quiz_expired_challenge(self, mock_quiz_service):
        """Test quiz submission with expired challenge."""
        challenge_id = "quiz_123"

        # Mock expired challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": "user_123",
            "correct_answers": {},
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "terms": {},
            "difficulty": "beginner"
        }

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[],
            time_taken_seconds=45
        )

        with pytest.raises(ValidationError, match="expired"):
            mock_quiz_service.submit_quiz("user_123", submission)

    def test_submit_quiz_partial_correct(self, mock_quiz_service):
        """Test quiz submission with partial correct answers."""
        challenge_id = "quiz_123"
        user_id = "user_456"

        # Mock active challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": {"q1": "a", "q2": "b"},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {"q1": "bussin", "q2": "cap"},
            "difficulty": "beginner"
        }

        # Mock repository methods
        mock_quiz_service.repository.save_quiz_result.return_value = True
        mock_quiz_service.repository.increment_daily_quiz_count.return_value = 2
        mock_quiz_service.repository.get_term_by_slang.side_effect = [
            {"meaning": "Really good"},
            {"meaning": "Lie"}
        ]

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[
                QuizAnswer(question_id="q1", selected="a"),  # Correct
                QuizAnswer(question_id="q2", selected="c")   # Wrong
            ],
            time_taken_seconds=30
        )

        result = mock_quiz_service.submit_quiz(user_id, submission)

        assert result.correct_count == 1
        assert result.total_questions == 2
        assert result.score == 15  # 1 correct * 10 + time bonus
        assert result.results[0].is_correct is True
        assert result.results[1].is_correct is False

    def test_submit_quiz_time_bonus(self, mock_quiz_service):
        """Test quiz submission with time bonus."""
        challenge_id = "quiz_123"
        user_id = "user_456"

        # Mock active challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": {"q1": "a"},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {"q1": "bussin"},
            "difficulty": "beginner"
        }

        # Mock repository methods
        mock_quiz_service.repository.save_quiz_result.return_value = True
        mock_quiz_service.repository.increment_daily_quiz_count.return_value = 2
        mock_quiz_service.repository.get_term_by_slang.return_value = {"meaning": "Really good"}

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[QuizAnswer(question_id="q1", selected="a")],
            time_taken_seconds=30  # 30 seconds saved = 5 bonus points
        )

        result = mock_quiz_service.submit_quiz(user_id, submission)

        assert result.time_bonus_points == 5  # 30 seconds / 6 = 5 points
        assert result.score == 15  # 10 base + 5 bonus

    def test_submit_quiz_cleans_up_challenge(self, mock_quiz_service):
        """Test that completed challenge is removed from active challenges."""
        challenge_id = "quiz_123"
        user_id = "user_456"

        # Mock active challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": {"q1": "a"},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {"q1": "bussin"},
            "difficulty": "beginner"
        }

        # Mock repository methods
        mock_quiz_service.repository.save_quiz_result.return_value = True
        mock_quiz_service.repository.increment_daily_quiz_count.return_value = 2
        mock_quiz_service.repository.get_term_by_slang.return_value = {"meaning": "Really good"}

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[QuizAnswer(question_id="q1", selected="a")],
            time_taken_seconds=45
        )

        mock_quiz_service.submit_quiz(user_id, submission)

        # Challenge should be removed
        assert challenge_id not in mock_quiz_service._active_challenges

    def test_submit_quiz_updates_term_statistics(self, mock_quiz_service):
        """Test that quiz submission updates term statistics."""
        challenge_id = "quiz_123"
        user_id = "user_456"

        # Mock active challenge
        mock_quiz_service._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": {"q1": "a"},
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "terms": {"q1": "bussin"},
            "difficulty": "beginner"
        }

        # Mock repository methods
        mock_quiz_service.repository.save_quiz_result.return_value = True
        mock_quiz_service.repository.increment_daily_quiz_count.return_value = 2
        mock_quiz_service.repository.get_term_by_slang.return_value = {"meaning": "Really good"}

        submission = QuizSubmissionRequest(
            challenge_id=challenge_id,
            answers=[QuizAnswer(question_id="q1", selected="a")],
            time_taken_seconds=45
        )

        mock_quiz_service.submit_quiz(user_id, submission)

        # Should update statistics for the term
        mock_quiz_service.repository.update_quiz_statistics.assert_called_once_with("bussin", True)
