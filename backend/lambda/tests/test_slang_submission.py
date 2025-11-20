"""Tests for slang submission feature."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangSubmission,
    SlangSubmissionRequest,
    SlangSubmissionResponse,
    ApprovalStatus,
    SubmissionContext,
)
from models.users import User, UserTier, UserStatus
from services.slang_submission_service import SlangSubmissionService
from utils.exceptions import (
    ValidationError,
    InsufficientPermissionsError,
    BusinessLogicError,
)


class TestSlangSubmissionService:
    """Test SlangSubmissionService."""

    @pytest.fixture
    def submission_service(self, mock_config):
        """Create SlangSubmissionService with mocked dependencies."""
        with patch('services.slang_submission_service.SubmissionsRepository') as mock_repo_class:
            with patch('services.slang_submission_service.UserService') as mock_user_service_class:
                with patch('services.slang_submission_service.get_config_service') as mock_get_config:
                    with patch('services.slang_submission_service.aws_services') as mock_aws_services:
                        mock_get_config.return_value = mock_config

                        # Create mock instances
                        mock_repo = Mock()
                        mock_repo_class.return_value = mock_repo

                        mock_user_service = Mock()
                        mock_user_service_class.return_value = mock_user_service

                        mock_sns = Mock()
                        mock_aws_services.sns_client = mock_sns

                        service = SlangSubmissionService()
                        return service

    @pytest.fixture
    def sample_premium_user(self):
        """Create a sample premium user."""
        return User(
            user_id="premium_user_123",
            email="premium@test.com",
            username="premiumuser",
            tier=UserTier.PREMIUM,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def sample_free_user(self):
        """Create a sample free user."""
        return User(
            user_id="free_user_123",
            email="free@test.com",
            username="freeuser",
            tier=UserTier.FREE,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def valid_submission_request(self):
        """Create a valid submission request."""
        return SlangSubmissionRequest(
            slang_term="bussin",
            meaning="Really good, amazing, excellent",
            example_usage="This pizza is bussin, no cap!",
            context=SubmissionContext.MANUAL,
        )

    def test_premium_user_can_submit_slang(
        self, submission_service, sample_premium_user, valid_submission_request
    ):
        """Test that premium users can submit slang successfully."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'config_service') as mock_config:
                    mock_user_service.get_user.return_value = sample_premium_user
                    mock_repo.check_duplicate_submission.return_value = False
                    mock_repo.generate_submission_id.return_value = "sub_123456"
                    mock_repo.create_submission.return_value = True
                    mock_config._get_env_var.return_value = "arn:aws:sns:us-east-1:123456:test"

                    result = submission_service.submit_slang(
                        valid_submission_request, sample_premium_user.user_id
                    )

                    # Verify response
                    assert isinstance(result, SlangSubmissionResponse)
                    assert result.submission_id == "sub_123456"
                    assert result.status == ApprovalStatus.PENDING
                    assert "community will vote" in result.message.lower()

                    # Verify submission was created
                    mock_repo.create_submission.assert_called_once()

    def test_free_user_cannot_submit_slang(
        self, submission_service, sample_free_user, valid_submission_request
    ):
        """Test that free users cannot submit slang."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            mock_user_service.get_user.return_value = sample_free_user

            with pytest.raises(InsufficientPermissionsError) as exc_info:
                submission_service.submit_slang(
                    valid_submission_request, sample_free_user.user_id
                )

            assert "premium feature" in exc_info.value.message.lower()

    def test_duplicate_submission_rejected(
        self, submission_service, sample_premium_user, valid_submission_request
    ):
        """Test that duplicate submissions are rejected."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                mock_user_service.get_user.return_value = sample_premium_user
                mock_repo.check_duplicate_submission.return_value = True  # Duplicate found

                with pytest.raises(ValidationError) as exc_info:
                    submission_service.submit_slang(
                        valid_submission_request, sample_premium_user.user_id
                    )

                assert "already submitted" in exc_info.value.message.lower()

    def test_rate_limit_enforced(
        self, submission_service, sample_premium_user, valid_submission_request
    ):
        """Test that rate limiting is enforced."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, '_check_rate_limit') as mock_rate_limit:
                    mock_user_service.get_user.return_value = sample_premium_user
                    mock_repo.check_duplicate_submission.return_value = False
                    mock_rate_limit.return_value = False  # Rate limit exceeded

                    with pytest.raises(BusinessLogicError) as exc_info:
                        submission_service.submit_slang(
                            valid_submission_request, sample_premium_user.user_id
                        )

                    assert "daily limit" in exc_info.value.message.lower()

    def test_empty_slang_term_rejected(self):
        """Test that empty slang term is rejected by Pydantic validation."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            SlangSubmissionRequest(
                slang_term="",
                meaning="Test meaning",
                context=SubmissionContext.MANUAL,
            )

    def test_empty_meaning_rejected(self):
        """Test that empty meaning is rejected by Pydantic validation."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            SlangSubmissionRequest(
                slang_term="test",
                meaning="",
                context=SubmissionContext.MANUAL,
            )

    def test_sns_notification_sent(
        self, submission_service, sample_premium_user, valid_submission_request
    ):
        """Test that SNS notification is sent on successful submission."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'sns_client') as mock_sns:
                    with patch.object(submission_service, 'config_service') as mock_config:
                        mock_user_service.get_user.return_value = sample_premium_user
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo.generate_submission_id.return_value = "sub_test"
                        mock_repo.create_submission.return_value = True
                        mock_config._get_env_var.return_value = "arn:aws:sns:us-east-1:123456:test"

                        result = submission_service.submit_slang(
                            valid_submission_request, sample_premium_user.user_id
                        )

                        # Verify SNS was called
                        mock_sns.publish.assert_called_once()
                        call_args = mock_sns.publish.call_args
                        assert "bussin" in call_args.kwargs['Subject']

    def test_sns_failure_doesnt_block_submission(
        self, submission_service, sample_premium_user, valid_submission_request
    ):
        """Test that SNS failures don't prevent successful submission."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'sns_client') as mock_sns:
                    with patch.object(submission_service, 'config_service') as mock_config:
                        mock_user_service.get_user.return_value = sample_premium_user
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo.generate_submission_id.return_value = "sub_sns_fail"
                        mock_repo.create_submission.return_value = True
                        mock_config._get_env_var.return_value = "arn:aws:sns:us-east-1:123456:test"

                        # Make SNS fail
                        mock_sns.publish.side_effect = Exception("SNS error")

                        # Should still succeed
                        result = submission_service.submit_slang(
                            valid_submission_request, sample_premium_user.user_id
                        )

                        assert result.submission_id == "sub_sns_fail"
                        assert result.status == ApprovalStatus.PENDING

    def test_translation_failure_context_tracked(
        self, submission_service, sample_premium_user
    ):
        """Test that translation failure context is properly tracked."""
        request = SlangSubmissionRequest(
            slang_term="new slang",
            meaning="Some meaning",
            example_usage="Example here",
            context=SubmissionContext.TRANSLATION_FAILURE,
            translation_id="trans_failed_123",
        )

        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'config_service') as mock_config:
                    mock_user_service.get_user.return_value = sample_premium_user
                    mock_repo.check_duplicate_submission.return_value = False
                    mock_repo.generate_submission_id.return_value = "sub_ctx"
                    mock_repo.create_submission.return_value = True
                    mock_config._get_env_var.return_value = "arn:aws:sns:us-east-1:123456:test"

                    result = submission_service.submit_slang(
                        request, sample_premium_user.user_id
                    )

                    # Verify submission was created with context
                    create_call = mock_repo.create_submission.call_args[0][0]
                    assert create_call.context == SubmissionContext.TRANSLATION_FAILURE
                    assert create_call.original_translation_id == "trans_failed_123"

    def test_get_user_submissions_premium_only(
        self, submission_service, sample_free_user
    ):
        """Test that only premium users can view their submissions."""
        with patch.object(submission_service, 'user_service') as mock_user_service:
            mock_user_service.get_user.return_value = sample_free_user

            with pytest.raises(InsufficientPermissionsError):
                submission_service.get_user_submissions(sample_free_user.user_id)

    def test_check_rate_limit_allows_within_limit(self, submission_service):
        """Test that submissions are allowed when under rate limit."""
        user_id = "test_user"

        with patch.object(submission_service, 'repository') as mock_repo:
            # Return 5 submissions (under limit of 10)
            mock_submissions = [
                Mock(created_at=datetime.now(timezone.utc))
                for _ in range(5)
            ]
            mock_repo.get_user_submissions.return_value = mock_submissions

            result = submission_service._check_rate_limit(user_id)

            assert result is True

    def test_check_rate_limit_blocks_when_exceeded(self, submission_service):
        """Test that submissions are blocked when rate limit exceeded."""
        user_id = "test_user"

        with patch.object(submission_service, 'repository') as mock_repo:
            # Return 10 submissions (at limit)
            mock_submissions = [
                Mock(created_at=datetime.now(timezone.utc))
                for _ in range(10)
            ]
            mock_repo.get_user_submissions.return_value = mock_submissions

            result = submission_service._check_rate_limit(user_id)

            assert result is False

    def test_validate_submission_max_lengths(self):
        """Test that maximum length validation works via Pydantic."""
        from pydantic import ValidationError as PydanticValidationError

        # Test slang term too long - Pydantic validates this
        with pytest.raises(PydanticValidationError):
            SlangSubmissionRequest(
                slang_term="x" * 101,  # Over 100 char limit
                meaning="test",
                context=SubmissionContext.MANUAL,
            )

        # Test meaning too long - Pydantic validates this
        with pytest.raises(PydanticValidationError):
            SlangSubmissionRequest(
                slang_term="test",
                meaning="x" * 501,  # Over 500 char limit
                context=SubmissionContext.MANUAL,
            )
