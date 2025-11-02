"""Tests for SlangTermRepository."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangSubmission,
    ApprovalStatus,
    SlangSubmissionStatus,
    ApprovalType,
    SubmissionContext,
    LLMValidationResult,
    LLMValidationEvidence,
)
from models.quiz import QuizDifficulty


class TestSlangTermRepository:
    """Test SlangTermRepository functionality."""

    @pytest.fixture
    def mock_repository(self):
        """Create mocked SlangTermRepository."""
        with patch('repositories.slang_term_repository.get_config_service') as mock_config:
            with patch('repositories.slang_term_repository.aws_services') as mock_aws:
                # Setup config mock
                mock_config_service = Mock()
                mock_config_service._get_env_var.return_value = "test-terms-table"
                mock_config.return_value = mock_config_service

                # Setup AWS services mock
                mock_table = Mock()
                mock_aws.get_table.return_value = mock_table

                from repositories.slang_term_repository import SlangTermRepository
                repo = SlangTermRepository()
                repo.table = mock_table
                return repo

    @pytest.fixture
    def sample_submission(self):
        """Sample slang submission for testing."""
        return SlangSubmission(
            submission_id="sub_123",
            user_id="user_456",
            slang_term="bussin",
            meaning="Really good",
            example_usage="That pizza was bussin!",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            llm_validation_status=SlangSubmissionStatus.PENDING_VALIDATION,
            created_at=datetime.now(timezone.utc),
            upvotes=0,
            upvoted_by=[],
        )

    def test_generate_submission_id(self, mock_repository):
        """Test submission ID generation."""
        submission_id = mock_repository.generate_submission_id()
        assert submission_id.startswith("sub_")
        assert len(submission_id) == 20  # "sub_" + 16 hex chars

    def test_create_submission_success(self, mock_repository, sample_submission):
        """Test successful submission creation."""
        mock_repository.table.put_item.return_value = {}

        result = mock_repository.create_submission(sample_submission)

        assert result is True
        mock_repository.table.put_item.assert_called_once()

        # Verify the item structure
        call_args = mock_repository.table.put_item.call_args[1]["Item"]
        assert call_args["PK"] == f"TERM#{sample_submission.slang_term.lower()}"
        assert call_args["SK"] == f"SOURCE#user#{sample_submission.submission_id}"
        assert call_args["submission_id"] == sample_submission.submission_id
        assert call_args["source"] == "user_submission"

    def test_create_submission_failure(self, mock_repository, sample_submission):
        """Test submission creation failure."""
        mock_repository.table.put_item.side_effect = Exception("DynamoDB error")

        result = mock_repository.create_submission(sample_submission)

        assert result is False

    def test_get_submission_by_id_found(self, mock_repository, sample_submission):
        """Test getting existing submission by ID."""
        # Mock DynamoDB response
        mock_item = {
            "PK": f"TERM#{sample_submission.slang_term.lower()}",
            "SK": f"SOURCE#user#{sample_submission.submission_id}",
            "submission_id": sample_submission.submission_id,
            "user_id": sample_submission.user_id,
            "slang_term": sample_submission.slang_term,
            "meaning": sample_submission.meaning,
            "example_usage": sample_submission.example_usage,
            "context": str(sample_submission.context),
            "status": str(sample_submission.status),
            "created_at": sample_submission.created_at.isoformat(),
            "source": "user_submission",
        }

        mock_repository.table.scan.return_value = {"Items": [mock_item]}

        result = mock_repository.get_submission_by_id("sub_123")

        assert result is not None
        assert result.submission_id == "sub_123"
        assert result.slang_term == "bussin"

    def test_get_submission_by_id_not_found(self, mock_repository):
        """Test getting non-existent submission."""
        mock_repository.table.scan.return_value = {"Items": []}

        result = mock_repository.get_submission_by_id("nonexistent")

        assert result is None

    def test_get_pending_submissions(self, mock_repository, sample_submission):
        """Test getting pending submissions."""
        mock_item = {
            "PK": f"TERM#{sample_submission.slang_term.lower()}",
            "SK": f"SOURCE#user#{sample_submission.submission_id}",
            "submission_id": sample_submission.submission_id,
            "user_id": sample_submission.user_id,
            "slang_term": sample_submission.slang_term,
            "meaning": sample_submission.meaning,
            "context": str(sample_submission.context),
            "status": "pending",
            "created_at": sample_submission.created_at.isoformat(),
            "source": "user_submission",
            "GSI1PK": "STATUS#pending",
            "GSI1SK": sample_submission.created_at.isoformat(),
        }

        mock_repository.table.query.return_value = {"Items": [mock_item]}

        result = mock_repository.get_pending_submissions(limit=10)

        assert len(result) == 1
        assert result[0].submission_id == "sub_123"
        mock_repository.table.query.assert_called_once()

    def test_update_validation_result(self, mock_repository):
        """Test updating submission with validation result."""
        validation_result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.95"),
            evidence=[
                LLMValidationEvidence(
                    source="urban_dictionary",
                    example="That food was bussin",
                    relevance_score=Decimal("0.9"),
                )
            ],
            recommended_definition=None,
            usage_score=9,
            validated_at=datetime.now(timezone.utc),
        )

        # Mock finding the submission
        mock_repository.table.scan.return_value = {
            "Items": [{
                "PK": "TERM#bussin",
                "SK": "SOURCE#user#sub_123",
            }]
        }

        result = mock_repository.update_validation_result("sub_123", "user_456", validation_result)

        assert result is True
        mock_repository.table.update_item.assert_called_once()

    def test_upvote_submission(self, mock_repository):
        """Test upvoting a submission."""
        # Mock finding the submission
        mock_repository.table.scan.return_value = {
            "Items": [{
                "PK": "TERM#bussin",
                "SK": "SOURCE#user#sub_123",
            }]
        }

        result = mock_repository.upvote_submission("sub_123", "user_456")

        assert result is True
        mock_repository.table.update_item.assert_called_once()

    def test_create_lexicon_term(self, mock_repository):
        """Test creating lexicon term."""
        term_data = {
            "PK": "TERM#bussin",
            "SK": "SOURCE#lexicon#bussin",
            "slang_term": "bussin",
            "meaning": "Really good",
            "source": "lexicon",
            "status": "approved",
        }

        result = mock_repository.create_lexicon_term(term_data)

        assert result is True
        mock_repository.table.put_item.assert_called_once_with(Item=term_data)

    def test_get_all_lexicon_terms(self, mock_repository):
        """Test getting all lexicon terms."""
        mock_items = [
            {
                "PK": "TERM#bussin",
                "SK": "SOURCE#lexicon#bussin",
                "slang_term": "bussin",
                "source": "lexicon",
            },
            {
                "PK": "TERM#cap",
                "SK": "SOURCE#lexicon#cap",
                "slang_term": "cap",
                "source": "lexicon",
            }
        ]

        mock_repository.table.query.return_value = {"Items": mock_items}

        result = mock_repository.get_all_lexicon_terms()

        assert len(result) == 2
        assert all(item["source"] == "lexicon" for item in result)

    def test_get_quiz_eligible_terms(self, mock_repository):
        """Test getting quiz eligible terms by difficulty."""
        mock_items = [
            {
                "slang_term": "bussin",
                "meaning": "Really good",
                "is_quiz_eligible": True,
                "quiz_difficulty": "beginner",
                "quiz_category": "approval",
            }
        ]

        mock_repository.table.query.return_value = {"Items": mock_items}

        result = mock_repository.get_quiz_eligible_terms(QuizDifficulty.BEGINNER, limit=5)

        assert len(result) == 1
        assert result[0]["is_quiz_eligible"] is True

    def test_get_terms_by_category_keys_only_fallback(self, mock_repository):
        """Test get_terms_by_category handles KEYS_ONLY projection by fetching full items."""
        # GSI3 returns KEYS_ONLY, so items will only have PK and SK
        mock_items = [
            {"PK": "TERM#bussin", "SK": "SOURCE#lexicon#bussin"},
            {"PK": "TERM#cap", "SK": "SOURCE#lexicon#cap"},
        ]

        # Full items that should be returned after GetItem
        full_items = {
            ("TERM#bussin", "SOURCE#lexicon#bussin"): {
                "PK": "TERM#bussin",
                "SK": "SOURCE#lexicon#bussin",
                "slang_term": "bussin",
                "meaning": "Really good",
                "quiz_category": "approval",
            },
            ("TERM#cap", "SOURCE#lexicon#cap"): {
                "PK": "TERM#cap",
                "SK": "SOURCE#lexicon#cap",
                "slang_term": "cap",
                "meaning": "Lie",
                "quiz_category": "disapproval",
            },
        }

        mock_repository.table.query.return_value = {"Items": mock_items}
        # Mock GetItem to return full items
        def mock_get_item(**kwargs):
            key = kwargs.get("Key", {})
            pk = key.get("PK")
            sk = key.get("SK")
            return {"Item": full_items.get((pk, sk), {})}

        mock_repository.table.get_item = mock_get_item

        result = mock_repository.get_terms_by_category("approval", limit=10)

        # Should return full items with meaning and slang_term
        assert len(result) == 2
        assert all("meaning" in item for item in result)
        assert all("slang_term" in item for item in result)

    def test_save_quiz_result(self, mock_repository):
        """Test saving quiz result."""
        quiz_result = {
            "quiz_id": "quiz_123",
            "score": 85,
            "total_possible": 100,
            "correct_count": 8,
            "total_questions": 10,
            "time_taken_seconds": 45,
            "difficulty": "beginner",
            "challenge_type": "multiple_choice",
        }

        result = mock_repository.save_quiz_result("user_456", quiz_result)

        assert result is True
        mock_repository.table.put_item.assert_called_once()

    def test_get_daily_quiz_count(self, mock_repository):
        """Test getting daily quiz count."""
        mock_repository.table.get_item.return_value = {
            "Item": {"quiz_count": 2}
        }

        result = mock_repository.get_daily_quiz_count("user_456", "2024-01-15")

        assert result == 2

    def test_get_daily_quiz_count_not_found(self, mock_repository):
        """Test getting daily quiz count when no record exists."""
        mock_repository.table.get_item.return_value = {}

        result = mock_repository.get_daily_quiz_count("user_456", "2024-01-15")

        assert result == 0

    def test_increment_daily_quiz_count(self, mock_repository):
        """Test incrementing daily quiz count."""
        mock_repository.table.update_item.return_value = {
            "Attributes": {"quiz_count": 3}
        }

        result = mock_repository.increment_daily_quiz_count("user_456")

        assert result == 3
        mock_repository.table.update_item.assert_called_once()

    def test_get_user_quiz_stats(self, mock_repository):
        """Test getting user quiz statistics."""
        # Mock quiz history
        history_items = [
            {
                "score": 80,
                "total_possible": 100,
                "correct_count": 8,
                "total_questions": 10,
            },
            {
                "score": 90,
                "total_possible": 100,
                "correct_count": 9,
                "total_questions": 10,
            }
        ]

        mock_repository.table.query.return_value = {"Items": history_items}

        result = mock_repository.get_user_quiz_stats("user_456")

        assert result["total_quizzes"] == 2
        assert result["total_correct"] == 17
        assert result["total_questions"] == 20
        assert result["accuracy_rate"] == 0.85  # 17/20

    def test_get_all_approved_terms(self, mock_repository):
        """Test getting all approved terms for export."""
        mock_items = [
            {
                "slang_term": "bussin",
                "meaning": "Really good",
                "status": "approved",
                "source": "lexicon",
            },
            {
                "slang_term": "cap",
                "meaning": "Lie",
                "status": "approved",
                "source": "user_submission",
            }
        ]

        mock_repository.table.scan.return_value = {"Items": mock_items}

        result = mock_repository.get_all_approved_terms()

        assert len(result) == 2
        assert all(item["status"] == "approved" for item in result)

    def test_mark_exported(self, mock_repository):
        """Test marking term as exported."""
        # Mock finding the term
        mock_repository.table.query.return_value = {
            "Items": [{
                "PK": "TERM#bussin",
                "SK": "SOURCE#lexicon#bussin",
            }]
        }

        mock_repository.mark_exported("bussin", "lexicon")

        mock_repository.table.update_item.assert_called_once()

    def test_check_duplicate_submission_exists(self, mock_repository):
        """Test checking for duplicate submission when it exists."""
        mock_repository.table.query.return_value = {
            "Items": [{"submission_id": "existing_sub"}]
        }

        result = mock_repository.check_duplicate_submission("bussin", "user_456", days=7)

        assert result is True

    def test_check_duplicate_submission_not_exists(self, mock_repository):
        """Test checking for duplicate submission when it doesn't exist."""
        mock_repository.table.query.return_value = {"Items": []}

        result = mock_repository.check_duplicate_submission("bussin", "user_456", days=7)

        assert result is False

    def test_update_quiz_statistics(self, mock_repository):
        """Test updating quiz statistics for a term."""
        # Mock finding the term
        mock_repository.table.query.return_value = {
            "Items": [{
                "PK": "TERM#bussin",
                "SK": "SOURCE#lexicon#bussin",
                "times_in_quiz": 5,
                "quiz_accuracy_rate": 0.8,
            }]
        }

        mock_repository.update_quiz_statistics("bussin", True)

        mock_repository.table.update_item.assert_called_once()

    def test_get_terms_by_category(self, mock_repository):
        """Test getting terms by category."""
        mock_items = [
            {
                "slang_term": "bussin",
                "meaning": "Really good",
                "quiz_category": "approval",
            }
        ]

        mock_repository.table.query.return_value = {"Items": mock_items}

        result = mock_repository.get_terms_by_category("approval", limit=10)

        assert len(result) == 1
        assert result[0]["quiz_category"] == "approval"
