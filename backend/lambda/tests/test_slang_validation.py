"""Tests for slang validation and crowdsourcing features."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangSubmission,
    SlangSubmissionRequest,
    SlangSubmissionResponse,
    SlangSubmissionStatus,
    ApprovalStatus,
    ApprovalType,
    SubmissionContext,
    LLMValidationResult,
    LLMValidationEvidence,
    UpvoteResponse,
    PendingSubmissionsResponse,
    AdminApprovalResponse,
)
from models.users import User, UserTier, UserStatus
from utils.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)


class TestSlangValidationService:
    """Test SlangValidationService."""

    @pytest.fixture
    def validation_service(self, mock_config):
        """Create SlangValidationService with mocked dependencies."""
        from services.slang_validation_service import SlangValidationService

        with patch('services.slang_validation_service.get_config_service') as mock_get_config:
            with patch('services.slang_validation_service.aws_services') as mock_aws_services:
                mock_get_config.return_value = mock_config

                # Mock validation config
                mock_validation_config = Mock()
                mock_validation_config.auto_approval_enabled = True
                mock_validation_config.auto_approval_threshold = 0.85
                mock_validation_config.web_search_enabled = True
                mock_validation_config.max_search_results = 5
                mock_validation_config.tavily_api_key = "test-api-key"

                # Mock LLM config
                mock_llm_config = Mock()
                mock_llm_config.model = "anthropic.claude-3-haiku-20240307-v1:0"
                mock_llm_config.max_tokens = 500
                mock_llm_config.temperature = 0.3
                mock_llm_config.top_p = 0.9

                mock_config.get_config.side_effect = lambda config_type: (
                    mock_validation_config if config_type.__name__ == 'SlangValidationConfig'
                    else mock_llm_config
                )

                mock_bedrock = Mock()
                mock_aws_services.bedrock_client = mock_bedrock

                service = SlangValidationService()
                return service

    @pytest.fixture
    def sample_submission(self):
        """Create a sample slang submission."""
        return SlangSubmission(
            submission_id="sub_test123",
            user_id="user_123",
            slang_term="bussin",
            meaning="Really good, amazing",
            example_usage="This pizza is bussin!",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewed_by=None,
            llm_validation_status=SlangSubmissionStatus.PENDING_VALIDATION,
            llm_confidence_score=None,
            llm_validation_result=None,
            approval_type=None,
            approved_by=None,
            upvotes=0,
            upvoted_by=[],
        )

    def test_validate_submission_with_web_search(self, validation_service, sample_submission):
        """Test validation with web search enabled."""
        with patch.object(validation_service, '_web_search') as mock_search:
            with patch.object(validation_service, '_call_claude') as mock_claude:
                # Mock web search results
                mock_search.return_value = [
                    {
                        "url": "https://urbandictionary.com/bussin",
                        "content": "Bussin means really good",
                        "title": "Bussin - Urban Dictionary"
                    }
                ]

                # Mock Claude response
                mock_claude.return_value = LLMValidationResult(
                    is_valid=True,
                    confidence=Decimal("0.95"),
                    evidence=[
                        LLMValidationEvidence(
                            source="urbandictionary.com",
                            example="Found in Urban Dictionary with 10k upvotes"
                        )
                    ],
                    recommended_definition=None,
                    usage_score=9,
                    validated_at=datetime.now(timezone.utc),
                )

                result = validation_service.validate_submission(sample_submission)

                assert result.is_valid is True
                assert result.confidence == Decimal("0.95")
                assert result.usage_score == 9
                mock_search.assert_called_once_with("bussin")
                mock_claude.assert_called_once()

    def test_validate_submission_without_web_search(self, validation_service, sample_submission):
        """Test validation without web search (disabled or no API key)."""
        validation_service.validation_config.web_search_enabled = False

        with patch.object(validation_service, '_call_claude') as mock_claude:
            mock_claude.return_value = LLMValidationResult(
                is_valid=True,
                confidence=Decimal("0.60"),
                evidence=[],
                recommended_definition=None,
                usage_score=5,
                validated_at=datetime.now(timezone.utc),
            )

            result = validation_service.validate_submission(sample_submission)

            # Should call Claude with empty search results
            assert result.confidence == Decimal("0.60")
            mock_claude.assert_called_once()
            call_args = mock_claude.call_args[0]
            assert call_args[1] == []  # Empty search results

    def test_should_auto_approve_high_confidence(self, validation_service):
        """Test that high confidence submissions are auto-approved."""
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.95"),
            evidence=[],
            recommended_definition=None,
            usage_score=9,
            validated_at=datetime.now(timezone.utc),
        )

        should_approve = validation_service.should_auto_approve(result)

        assert should_approve is True

    def test_should_not_auto_approve_low_confidence(self, validation_service):
        """Test that low confidence submissions are not auto-approved."""
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.70"),  # Below 0.85 threshold
            evidence=[],
            recommended_definition=None,
            usage_score=8,
            validated_at=datetime.now(timezone.utc),
        )

        should_approve = validation_service.should_auto_approve(result)

        assert should_approve is False

    def test_should_not_auto_approve_low_usage_score(self, validation_service):
        """Test that low usage score prevents auto-approval."""
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.95"),
            evidence=[],
            recommended_definition=None,
            usage_score=5,  # Below 7 threshold
            validated_at=datetime.now(timezone.utc),
        )

        should_approve = validation_service.should_auto_approve(result)

        assert should_approve is False

    def test_should_not_auto_approve_invalid(self, validation_service):
        """Test that invalid terms are not auto-approved."""
        result = LLMValidationResult(
            is_valid=False,
            confidence=Decimal("0.95"),
            evidence=[],
            recommended_definition=None,
            usage_score=9,
            validated_at=datetime.now(timezone.utc),
        )

        should_approve = validation_service.should_auto_approve(result)

        assert should_approve is False

    def test_determine_status_auto_approved(self, validation_service):
        """Test status determination for auto-approval."""
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.95"),
            evidence=[],
            recommended_definition=None,
            usage_score=9,
            validated_at=datetime.now(timezone.utc),
        )

        status = validation_service.determine_status(result)

        assert status == SlangSubmissionStatus.AUTO_APPROVED

    def test_determine_status_validated(self, validation_service):
        """Test status determination for validated (ready for voting)."""
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.70"),  # Valid but not auto-approve
            evidence=[],
            recommended_definition=None,
            usage_score=6,
            validated_at=datetime.now(timezone.utc),
        )

        status = validation_service.determine_status(result)

        assert status == SlangSubmissionStatus.VALIDATED

    def test_determine_status_rejected(self, validation_service):
        """Test status determination for rejected."""
        result = LLMValidationResult(
            is_valid=False,
            confidence=Decimal("0.30"),
            evidence=[],
            recommended_definition=None,
            usage_score=2,
            validated_at=datetime.now(timezone.utc),
        )

        status = validation_service.determine_status(result)

        assert status == SlangSubmissionStatus.REJECTED

    def test_fallback_validation(self, validation_service, sample_submission):
        """Test fallback validation when service unavailable."""
        result = validation_service._fallback_validation(sample_submission)

        assert result.is_valid is True
        assert result.confidence == Decimal("0.5")
        assert result.usage_score == 5
        assert len(result.evidence) > 0
        assert result.evidence[0].source == "fallback"


class TestSlangUpvoting:
    """Test slang upvoting functionality."""

    @pytest.fixture
    def submission_service(self, mock_config):
        """Create SlangSubmissionService with mocked dependencies."""
        from services.slang_submission_service import SlangSubmissionService

        with patch('services.slang_submission_service.SlangSubmissionRepository') as mock_repo_class:
            with patch('services.slang_submission_service.UserService') as mock_user_service_class:
                with patch('services.slang_submission_service.SlangValidationService') as mock_validation_class:
                    with patch('services.slang_submission_service.get_config_service') as mock_get_config:
                        with patch('services.slang_submission_service.aws_services') as mock_aws_services:
                            mock_get_config.return_value = mock_config

                            mock_repo = Mock()
                            mock_repo_class.return_value = mock_repo

                            mock_user_service = Mock()
                            mock_user_service_class.return_value = mock_user_service

                            mock_validation = Mock()
                            mock_validation_class.return_value = mock_validation

                            service = SlangSubmissionService()
                            return service

    @pytest.fixture
    def sample_submission(self):
        """Create a sample submission."""
        return SlangSubmission(
            submission_id="sub_123",
            user_id="owner_user",
            slang_term="bussin",
            meaning="Really good",
            example_usage="This is bussin!",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewed_by=None,
            llm_validation_status=SlangSubmissionStatus.VALIDATED,
            llm_confidence_score=Decimal("0.75"),
            llm_validation_result=None,
            approval_type=None,
            approved_by=None,
            upvotes=3,
            upvoted_by=["user1", "user2", "user3"],
        )

    def test_upvote_submission_success(self, submission_service, sample_submission):
        """Test successful upvote."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = sample_submission
            mock_repo.add_upvote.return_value = True

            # Create updated submission with incremented upvotes
            updated_submission = sample_submission.model_copy()
            updated_submission.upvotes = 4
            updated_submission.upvoted_by.append("voter_user")
            mock_repo.get_submission_by_id.side_effect = [sample_submission, updated_submission]

            result = submission_service.upvote_submission("sub_123", "voter_user")

            assert isinstance(result, UpvoteResponse)
            assert result.submission_id == "sub_123"
            assert result.upvotes == 4
            mock_repo.add_upvote.assert_called_once_with("sub_123", "owner_user", "voter_user")

    def test_cannot_upvote_own_submission(self, submission_service, sample_submission):
        """Test that users cannot upvote their own submissions."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = sample_submission

            with pytest.raises(ValidationError) as exc_info:
                submission_service.upvote_submission("sub_123", "owner_user")

            assert "can't upvote your own" in exc_info.value.message.lower()

    def test_cannot_upvote_twice(self, submission_service, sample_submission):
        """Test that users cannot upvote the same submission twice."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = sample_submission

            # Try to upvote as user1 who already upvoted
            with pytest.raises(ValidationError) as exc_info:
                submission_service.upvote_submission("sub_123", "user1")

            assert "already upvoted" in exc_info.value.message.lower()

    def test_upvote_nonexistent_submission(self, submission_service):
        """Test upvoting a submission that doesn't exist."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = None

            with pytest.raises(ResourceNotFoundError):
                submission_service.upvote_submission("sub_nonexistent", "voter_user")

    def test_get_pending_submissions(self, submission_service):
        """Test retrieving pending submissions for voting."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_submissions = [
                SlangSubmission(
                    submission_id=f"sub_{i}",
                    user_id=f"user_{i}",
                    slang_term=f"term{i}",
                    meaning=f"meaning{i}",
                    context=SubmissionContext.MANUAL,
                    status=ApprovalStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                    llm_validation_status=SlangSubmissionStatus.VALIDATED,
                    upvotes=i,
                    upvoted_by=[],
                )
                for i in range(5)
            ]
            mock_repo.get_by_validation_status.return_value = mock_submissions

            result = submission_service.get_pending_submissions(limit=10)

            assert isinstance(result, PendingSubmissionsResponse)
            assert len(result.submissions) == 5
            assert result.total_count == 5
            assert result.has_more is False
            mock_repo.get_by_validation_status.assert_called_once_with(
                SlangSubmissionStatus.VALIDATED, 10
            )


class TestAdminApprovalFeatures:
    """Test admin approval/rejection features."""

    @pytest.fixture
    def submission_service(self, mock_config):
        """Create SlangSubmissionService with mocked dependencies."""
        from services.slang_submission_service import SlangSubmissionService

        with patch('services.slang_submission_service.SlangSubmissionRepository') as mock_repo_class:
            with patch('services.slang_submission_service.UserService') as mock_user_service_class:
                with patch('services.slang_submission_service.SlangValidationService') as mock_validation_class:
                    with patch('services.slang_submission_service.get_config_service') as mock_get_config:
                        with patch('services.slang_submission_service.aws_services') as mock_aws_services:
                            mock_get_config.return_value = mock_config

                            mock_repo = Mock()
                            mock_repo_class.return_value = mock_repo

                            mock_user_service = Mock()
                            mock_user_service_class.return_value = mock_user_service

                            mock_validation = Mock()
                            mock_validation_class.return_value = mock_validation

                            service = SlangSubmissionService()
                            return service

    @pytest.fixture
    def sample_submission(self):
        """Create a sample submission."""
        return SlangSubmission(
            submission_id="sub_123",
            user_id="user_123",
            slang_term="bussin",
            meaning="Really good",
            example_usage="This is bussin!",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewed_by=None,
            llm_validation_status=SlangSubmissionStatus.VALIDATED,
            llm_confidence_score=Decimal("0.75"),
            llm_validation_result=None,
            approval_type=None,
            approved_by=None,
            upvotes=5,
            upvoted_by=["user1", "user2"],
        )

    def test_admin_approve_submission(self, submission_service, sample_submission):
        """Test admin manual approval."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = sample_submission
            mock_repo.update_approval_status.return_value = True
            mock_repo.update_submission_status.return_value = True

            result = submission_service.admin_approve("sub_123", "admin_user")

            assert isinstance(result, AdminApprovalResponse)
            assert result.submission_id == "sub_123"
            assert result.status == ApprovalStatus.APPROVED
            assert "approved" in result.message.lower()

            mock_repo.update_approval_status.assert_called_once_with(
                "sub_123",
                "user_123",
                SlangSubmissionStatus.ADMIN_APPROVED,
                ApprovalType.ADMIN_MANUAL,
                "admin_user",
            )

    def test_admin_reject_submission(self, submission_service, sample_submission):
        """Test admin manual rejection."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = sample_submission
            mock_repo.update_approval_status.return_value = True
            mock_repo.update_submission_status.return_value = True

            result = submission_service.admin_reject("sub_123", "admin_user")

            assert isinstance(result, AdminApprovalResponse)
            assert result.submission_id == "sub_123"
            assert result.status == ApprovalStatus.REJECTED
            assert "rejected" in result.message.lower()

            mock_repo.update_approval_status.assert_called_once_with(
                "sub_123",
                "user_123",
                SlangSubmissionStatus.REJECTED,
                ApprovalType.ADMIN_MANUAL,
                "admin_user",
            )

    def test_admin_approve_nonexistent_submission(self, submission_service):
        """Test approving a submission that doesn't exist."""
        with patch.object(submission_service, 'repository') as mock_repo:
            mock_repo.get_submission_by_id.return_value = None

            with pytest.raises(ResourceNotFoundError):
                submission_service.admin_approve("sub_nonexistent", "admin_user")


class TestAutoApprovalWorkflow:
    """Test the auto-approval workflow."""

    @pytest.fixture
    def submission_service(self, mock_config):
        """Create SlangSubmissionService with mocked dependencies."""
        from services.slang_submission_service import SlangSubmissionService

        with patch('services.slang_submission_service.SlangSubmissionRepository') as mock_repo_class:
            with patch('services.slang_submission_service.UserService') as mock_user_service_class:
                with patch('services.slang_submission_service.SlangValidationService') as mock_validation_class:
                    with patch('services.slang_submission_service.get_config_service') as mock_get_config:
                        with patch('services.slang_submission_service.aws_services') as mock_aws_services:
                            mock_get_config.return_value = mock_config

                            mock_repo = Mock()
                            mock_repo_class.return_value = mock_repo

                            mock_user_service = Mock()
                            mock_user_service_class.return_value = mock_user_service

                            mock_validation = Mock()
                            mock_validation_class.return_value = mock_validation

                            mock_sns = Mock()
                            mock_aws_services.sns_client = mock_sns

                            service = SlangSubmissionService()
                            return service

    @pytest.fixture
    def premium_user(self):
        """Create a premium user."""
        return User(
            user_id="premium_123",
            email="premium@test.com",
            username="premium",
            tier=UserTier.PREMIUM,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_high_confidence_auto_approval(
        self, submission_service, premium_user
    ):
        """Test that high-confidence submissions are auto-approved."""
        request = SlangSubmissionRequest(
            slang_term="rizz",
            meaning="Charisma, ability to attract",
            example_usage="He has rizz!",
            context=SubmissionContext.MANUAL,
        )

        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'validation_service') as mock_validation:
                    with patch.object(submission_service, 'config_service') as mock_config:
                        mock_user_service.get_user.return_value = premium_user
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo.generate_submission_id.return_value = "sub_auto"
                        mock_repo.create_submission.return_value = True
                        mock_repo.update_validation_result.return_value = True
                        mock_repo.update_approval_status.return_value = True
                        mock_config._get_env_var.return_value = "arn:aws:sns:test"

                        # Mock high-confidence validation
                        high_confidence_result = LLMValidationResult(
                            is_valid=True,
                            confidence=Decimal("0.95"),
                            evidence=[
                                LLMValidationEvidence(
                                    source="urbandictionary.com",
                                    example="Oxford Word of the Year 2023"
                                )
                            ],
                            recommended_definition=None,
                            usage_score=10,
                            validated_at=datetime.now(timezone.utc),
                        )
                        mock_validation.validate_submission.return_value = high_confidence_result
                        mock_validation.should_auto_approve.return_value = True
                        mock_validation.determine_status.return_value = SlangSubmissionStatus.AUTO_APPROVED

                        result = submission_service.submit_slang(request, premium_user.user_id)

                        assert isinstance(result, SlangSubmissionResponse)
                        assert result.status == ApprovalStatus.APPROVED
                        assert "auto-approved" in result.message.lower()

                        # Verify auto-approval was recorded
                        mock_repo.update_approval_status.assert_called_once()
                        call_args = mock_repo.update_approval_status.call_args[0]
                        assert call_args[2] == SlangSubmissionStatus.AUTO_APPROVED
                        assert call_args[3] == ApprovalType.LLM_AUTO

    def test_medium_confidence_requires_voting(
        self, submission_service, premium_user
    ):
        """Test that medium-confidence submissions require community voting."""
        request = SlangSubmissionRequest(
            slang_term="mid_term",
            meaning="Some meaning",
            context=SubmissionContext.MANUAL,
        )

        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'validation_service') as mock_validation:
                    with patch.object(submission_service, 'config_service') as mock_config:
                        mock_user_service.get_user.return_value = premium_user
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo.generate_submission_id.return_value = "sub_vote"
                        mock_repo.create_submission.return_value = True
                        mock_repo.update_validation_result.return_value = True
                        mock_repo.update_approval_status.return_value = True
                        mock_config._get_env_var.return_value = "arn:aws:sns:test"

                        # Mock medium-confidence validation
                        medium_confidence_result = LLMValidationResult(
                            is_valid=True,
                            confidence=Decimal("0.70"),
                            evidence=[],
                            recommended_definition=None,
                            usage_score=6,
                            validated_at=datetime.now(timezone.utc),
                        )
                        mock_validation.validate_submission.return_value = medium_confidence_result
                        mock_validation.should_auto_approve.return_value = False
                        mock_validation.determine_status.return_value = SlangSubmissionStatus.VALIDATED

                        result = submission_service.submit_slang(request, premium_user.user_id)

                        assert isinstance(result, SlangSubmissionResponse)
                        assert result.status == ApprovalStatus.PENDING
                        assert "community will vote" in result.message.lower()

                        # Verify status set to VALIDATED (ready for voting)
                        mock_repo.update_approval_status.assert_called_once()
                        call_args = mock_repo.update_approval_status.call_args[0]
                        assert call_args[2] == SlangSubmissionStatus.VALIDATED

    def test_low_confidence_rejected(
        self, submission_service, premium_user
    ):
        """Test that low-confidence submissions are rejected."""
        request = SlangSubmissionRequest(
            slang_term="fake_term",
            meaning="Made up",
            context=SubmissionContext.MANUAL,
        )

        with patch.object(submission_service, 'user_service') as mock_user_service:
            with patch.object(submission_service, 'repository') as mock_repo:
                with patch.object(submission_service, 'validation_service') as mock_validation:
                    with patch.object(submission_service, 'config_service') as mock_config:
                        mock_user_service.get_user.return_value = premium_user
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo.generate_submission_id.return_value = "sub_reject"
                        mock_repo.create_submission.return_value = True
                        mock_repo.update_validation_result.return_value = True
                        mock_repo.update_approval_status.return_value = True
                        mock_config._get_env_var.return_value = "arn:aws:sns:test"

                        # Mock low-confidence validation
                        low_confidence_result = LLMValidationResult(
                            is_valid=False,
                            confidence=Decimal("0.20"),
                            evidence=[],
                            recommended_definition=None,
                            usage_score=2,
                            validated_at=datetime.now(timezone.utc),
                        )
                        mock_validation.validate_submission.return_value = low_confidence_result
                        mock_validation.should_auto_approve.return_value = False
                        mock_validation.determine_status.return_value = SlangSubmissionStatus.REJECTED

                        result = submission_service.submit_slang(request, premium_user.user_id)

                        assert isinstance(result, SlangSubmissionResponse)
                        assert result.status == ApprovalStatus.REJECTED
                        assert "not sure this is gen z slang" in result.message.lower()


class TestSlangSubmissionRepository:
    """Test new repository methods for validation and upvoting."""

    @pytest.fixture
    def submission_repository(self, mock_config):
        """Create repository with mocked dependencies."""
        from repositories.slang_submission_repository import SlangSubmissionRepository

        with patch('repositories.slang_submission_repository.get_config_service') as mock_get_config:
            with patch('repositories.slang_submission_repository.aws_services') as mock_aws_services:
                mock_get_config.return_value = mock_config
                mock_config._get_env_var.return_value = "lingible-terms-test"

                mock_table = Mock()
                mock_aws_services.get_table.return_value = mock_table

                repo = SlangSubmissionRepository()
                return repo

    def test_add_upvote(self, submission_repository):
        """Test adding an upvote."""
        with patch.object(submission_repository, 'table') as mock_table:
            mock_table.update_item.return_value = {}

            result = submission_repository.add_upvote("sub_123", "owner_user", "voter_user")

            assert result is True
            mock_table.update_item.assert_called_once()

            # Verify the update expression includes upvotes and upvoted_by
            call_kwargs = mock_table.update_item.call_args.kwargs
            assert "upvotes" in call_kwargs['UpdateExpression']
            assert "upvoted_by" in call_kwargs['UpdateExpression']

    def test_get_by_validation_status(self, submission_repository):
        """Test querying by validation status."""
        with patch.object(submission_repository, 'table') as mock_table:
            mock_table.query.return_value = {
                'Items': [
                    {
                        'submission_id': 'sub_1',
                        'user_id': 'user_1',
                        'slang_term': 'term1',
                        'meaning': 'meaning1',
                        'context': 'manual',
                        'status': 'pending',
                        'llm_validation_status': 'validated',
                        'upvotes': 5,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }

            result = submission_repository.get_by_validation_status(
                SlangSubmissionStatus.VALIDATED, limit=50
            )

            assert len(result) == 1
            assert result[0].llm_validation_status == SlangSubmissionStatus.VALIDATED

            # Verify the query uses ValidationStatusIndex
            call_kwargs = mock_table.query.call_args.kwargs
            assert call_kwargs['IndexName'] == 'ValidationStatusIndex'

    def test_update_validation_result(self, submission_repository):
        """Test updating validation result."""
        validation_result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.85"),
            evidence=[
                LLMValidationEvidence(source="test.com", example="test example")
            ],
            recommended_definition=None,
            usage_score=8,
            validated_at=datetime.now(timezone.utc),
        )

        with patch.object(submission_repository, 'table') as mock_table:
            mock_table.update_item.return_value = {}

            result = submission_repository.update_validation_result(
                "sub_123", "user_123", validation_result
            )

            assert result is True
            mock_table.update_item.assert_called_once()

            # Verify the update includes confidence and result
            call_kwargs = mock_table.update_item.call_args.kwargs
            assert 'llm_confidence_score' in call_kwargs['UpdateExpression']
            assert 'llm_validation_result' in call_kwargs['UpdateExpression']

    def test_update_approval_status(self, submission_repository):
        """Test updating approval status."""
        with patch.object(submission_repository, 'table') as mock_table:
            mock_table.update_item.return_value = {}

            result = submission_repository.update_approval_status(
                "sub_123",
                "user_123",
                SlangSubmissionStatus.ADMIN_APPROVED,
                ApprovalType.ADMIN_MANUAL,
                "admin_user",
            )

            assert result is True
            mock_table.update_item.assert_called_once()

            # Verify the update includes all fields
            call_kwargs = mock_table.update_item.call_args.kwargs
            assert 'llm_validation_status' in call_kwargs['UpdateExpression']
            assert 'approval_type' in call_kwargs['UpdateExpression']
            assert 'approved_by' in call_kwargs['UpdateExpression']

    def test_get_submission_by_id(self, submission_repository):
        """Test getting submission by ID only (without user_id)."""
        with patch.object(submission_repository, 'table') as mock_table:
            mock_table.query.return_value = {
                'Items': [
                    {
                        'submission_id': 'sub_123',
                        'user_id': 'user_123',
                        'slang_term': 'test',
                        'meaning': 'test meaning',
                        'context': 'manual',
                        'status': 'pending',
                        'llm_validation_status': 'validated',
                        'upvotes': 3,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }

            result = submission_repository.get_submission_by_id("sub_123")

            assert result is not None
            assert result.submission_id == "sub_123"
            assert result.user_id == "user_123"

            # Verify query by PK only
            call_kwargs = mock_table.query.call_args.kwargs
            assert 'PK' in str(call_kwargs['KeyConditionExpression'])
