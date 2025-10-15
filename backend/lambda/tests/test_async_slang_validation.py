"""Tests for async slang validation processor and related functionality."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from models.slang import (
    SlangSubmission,
    SlangSubmissionStatus,
    ApprovalStatus,
    ApprovalType,
    SubmissionContext,
    LLMValidationResult,
    LLMValidationEvidence,
)
from models.events import SlangValidationEvent
from models.config import SlangSubmissionConfig


class TestValidationProcessorHandler:
    """Test the async validation processor Lambda handler."""

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

    @pytest.fixture
    def sample_validation_event(self):
        """Sample validation event from SNS."""
        return SlangValidationEvent(
            submission_id="sub_123",
            user_id="user_456",
            slang_term="bussin",
            context="manual",
        )

    @pytest.fixture
    def auto_approve_validation_result(self):
        """Validation result that should trigger auto-approval."""
        return LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.95"),  # High confidence
            evidence=[
                LLMValidationEvidence(
                    source="urban_dictionary",
                    example="That food was bussin",
                )
            ],
            recommended_definition=None,
            usage_score=9,  # High usage
            validated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def manual_review_validation_result(self):
        """Validation result that requires manual review."""
        return LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.70"),  # Medium confidence
            evidence=[],
            recommended_definition=None,
            usage_score=5,  # Medium usage
            validated_at=datetime.now(timezone.utc),
        )

    def test_handler_auto_approval_flow(
        self,
        sample_validation_event,
        sample_submission,
        auto_approve_validation_result,
    ):
        """Test handler auto-approves high-confidence submissions."""
        from handlers.slang_validation_processor.handler import lambda_handler

        # Mock dependencies
        with patch(
            "handlers.slang_validation_processor.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_processor.handler.SlangSubmissionService"
            ) as mock_submission_service_class:
                with patch(
                    "handlers.slang_validation_processor.handler.SlangSubmissionRepository"
                ) as mock_repo_class:
                    # Setup mocks
                    mock_repo = Mock()
                    mock_repo.get_submission_by_id.return_value = sample_submission
                    mock_repo_class.return_value = mock_repo

                    mock_validation_service = Mock()
                    mock_validation_service.validate_submission.return_value = (
                        auto_approve_validation_result
                    )
                    mock_validation_service.should_auto_approve.return_value = True
                    mock_validation_service.determine_status.return_value = (
                        SlangSubmissionStatus.AUTO_APPROVED
                    )
                    mock_validation_service_class.return_value = mock_validation_service

                    mock_submission_service = Mock()
                    mock_submission_service._publish_auto_approval_notification = Mock()
                    mock_submission_service.user_service = Mock()
                    mock_submission_service_class.return_value = mock_submission_service

                    # Execute handler
                    result = lambda_handler(sample_validation_event, Mock())

                    # Assertions
                    assert result["statusCode"] == 200
                    body = json.loads(result["body"])
                    assert body["message"] == "Validation completed"
                    assert body["auto_approved"] is True

                    # Verify validation was called
                    mock_validation_service.validate_submission.assert_called_once_with(
                        sample_submission
                    )

                    # Verify approval status updated with correct ApprovalType
                    mock_repo.update_approval_status.assert_called_once()
                    call_args = mock_repo.update_approval_status.call_args
                    assert call_args[0][3] == ApprovalType.LLM_AUTO

                    # Verify notifications sent
                    mock_submission_service._publish_auto_approval_notification.assert_called_once()

                    # Verify user stats updated
                    mock_submission_service.user_service.increment_slang_approved.assert_called_once_with(
                        "user_456"
                    )

    def test_handler_manual_review_flow(
        self,
        sample_validation_event,
        sample_submission,
        manual_review_validation_result,
    ):
        """Test handler routes low-confidence submissions to manual review."""
        from handlers.slang_validation_processor.handler import lambda_handler

        with patch(
            "handlers.slang_validation_processor.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_processor.handler.SlangSubmissionService"
            ) as mock_submission_service_class:
                with patch(
                    "handlers.slang_validation_processor.handler.SlangSubmissionRepository"
                ) as mock_repo_class:
                    # Setup mocks
                    mock_repo = Mock()
                    mock_repo.get_submission_by_id.return_value = sample_submission
                    mock_repo_class.return_value = mock_repo

                    mock_validation_service = Mock()
                    mock_validation_service.validate_submission.return_value = (
                        manual_review_validation_result
                    )
                    mock_validation_service.should_auto_approve.return_value = False
                    mock_validation_service.determine_status.return_value = (
                        SlangSubmissionStatus.VALIDATED
                    )
                    mock_validation_service_class.return_value = mock_validation_service

                    mock_submission_service = Mock()
                    mock_submission_service._publish_submission_notification = Mock()
                    mock_submission_service_class.return_value = mock_submission_service

                    # Execute handler
                    result = lambda_handler(sample_validation_event, Mock())

                    # Assertions
                    assert result["statusCode"] == 200
                    body = json.loads(result["body"])
                    assert body["auto_approved"] is False

                    # Verify validation result updated
                    assert mock_repo.update_validation_result.call_count == 2

                    # Verify admin notification sent (not auto-approval)
                    mock_submission_service._publish_submission_notification.assert_called_once_with(
                        sample_submission
                    )

    def test_handler_submission_not_found(self, sample_validation_event):
        """Test handler returns 404 when submission doesn't exist."""
        from handlers.slang_validation_processor.handler import lambda_handler

        with patch(
            "handlers.slang_validation_processor.handler.SlangValidationService"
        ):
            with patch(
                "handlers.slang_validation_processor.handler.SlangSubmissionService"
            ):
                with patch(
                    "handlers.slang_validation_processor.handler.SlangSubmissionRepository"
                ) as mock_repo_class:
                    mock_repo = Mock()
                    mock_repo.get_submission_by_id.return_value = None
                    mock_repo_class.return_value = mock_repo

                    result = lambda_handler(sample_validation_event, Mock())

                    assert result["statusCode"] == 404
                    body = json.loads(result["body"])
                    assert "not found" in body["error"].lower()

    def test_handler_validation_failure_uses_fallback(
        self, sample_validation_event, sample_submission
    ):
        """Test handler uses fallback validation on error."""
        from handlers.slang_validation_processor.handler import lambda_handler

        fallback_result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.5"),
            evidence=[],
            recommended_definition=None,
            usage_score=5,
            validated_at=datetime.now(timezone.utc),
        )

        with patch(
            "handlers.slang_validation_processor.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_processor.handler.SlangSubmissionService"
            ):
                with patch(
                    "handlers.slang_validation_processor.handler.SlangSubmissionRepository"
                ) as mock_repo_class:
                    # Setup mocks
                    mock_repo = Mock()
                    mock_repo.get_submission_by_id.return_value = sample_submission
                    mock_repo_class.return_value = mock_repo

                    mock_validation_service = Mock()
                    mock_validation_service.validate_submission.side_effect = Exception(
                        "Validation failed"
                    )
                    mock_validation_service._fallback_validation.return_value = (
                        fallback_result
                    )
                    mock_validation_service_class.return_value = mock_validation_service

                    # Execute handler
                    result = lambda_handler(sample_validation_event, Mock())

                    # Assertions
                    assert result["statusCode"] == 500

                    # Verify fallback was called WITH submission parameter
                    mock_validation_service._fallback_validation.assert_called_once_with(
                        sample_submission
                    )

                    # Verify fallback result was stored
                    mock_repo.update_validation_result.assert_called_once_with(
                        "sub_123", "user_456", fallback_result
                    )

    def test_validation_result_uses_confidence_attribute(
        self, auto_approve_validation_result
    ):
        """Test LLMValidationResult uses .confidence not .confidence_score."""
        # This would have caught the attribute name bug
        assert hasattr(auto_approve_validation_result, "confidence")
        assert not hasattr(auto_approve_validation_result, "confidence_score")
        assert auto_approve_validation_result.confidence == Decimal("0.95")

    def test_approval_type_on_submission_not_result(self, sample_submission):
        """Test approval_type is on SlangSubmission, not LLMValidationResult."""
        # This would have caught the wrong model bug
        result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.9"),
            evidence=[],
            recommended_definition=None,
            usage_score=8,
            validated_at=datetime.now(timezone.utc),
        )

        assert not hasattr(result, "approval_type")
        assert hasattr(sample_submission, "approval_type")


class TestSlangSubmissionConfig:
    """Test SlangSubmissionConfig model and integration."""

    def test_slang_submission_config_model(self):
        """Test SlangSubmissionConfig validates properly."""
        config = SlangSubmissionConfig(
            submissions_topic_arn="arn:aws:sns:us-east-1:123:submissions",
            validation_request_topic_arn="arn:aws:sns:us-east-1:123:validation",
        )

        assert config.submissions_topic_arn == "arn:aws:sns:us-east-1:123:submissions"
        assert (
            config.validation_request_topic_arn
            == "arn:aws:sns:us-east-1:123:validation"
        )

    def test_config_service_loads_submission_config(self):
        """Test ConfigService can load SlangSubmissionConfig from environment."""
        import os
        from utils.config import ConfigService

        # Set environment variables
        os.environ["SLANG_SUBMISSIONS_TOPIC_ARN"] = "arn:aws:sns:test:submissions"
        os.environ["SLANG_VALIDATION_REQUEST_TOPIC_ARN"] = "arn:aws:sns:test:validation"
        os.environ["ENVIRONMENT"] = "test"

        try:
            config_service = ConfigService()
            submission_config = config_service.get_config(SlangSubmissionConfig)

            assert (
                submission_config.submissions_topic_arn
                == "arn:aws:sns:test:submissions"
            )
            assert (
                submission_config.validation_request_topic_arn
                == "arn:aws:sns:test:validation"
            )
        finally:
            # Cleanup
            os.environ.pop("SLANG_SUBMISSIONS_TOPIC_ARN", None)
            os.environ.pop("SLANG_VALIDATION_REQUEST_TOPIC_ARN", None)

    def test_submission_service_uses_typed_config(self):
        """Test SlangSubmissionService uses typed config instead of os.environ."""
        from services.slang_submission_service import SlangSubmissionService

        with patch(
            "services.slang_submission_service.SlangSubmissionRepository"
        ) as mock_repo_class:
            with patch(
                "services.slang_submission_service.UserService"
            ) as mock_user_service_class:
                with patch(
                    "services.slang_submission_service.get_config_service"
                ) as mock_get_config:
                    with patch(
                        "services.slang_submission_service.aws_services"
                    ) as mock_aws_services:
                        # Setup config mock
                        mock_config = Mock()
                        mock_submission_config = SlangSubmissionConfig(
                            submissions_topic_arn="arn:aws:sns:test:submissions",
                            validation_request_topic_arn="arn:aws:sns:test:validation",
                        )
                        mock_config.get_config.return_value = mock_submission_config
                        mock_get_config.return_value = mock_config

                        # Create service
                        service = SlangSubmissionService()

                        # Verify config was loaded
                        assert service.submission_config == mock_submission_config
                        assert (
                            service.submission_config.submissions_topic_arn
                            == "arn:aws:sns:test:submissions"
                        )


class TestAsyncSubmissionFlow:
    """Test async submission flow publishes to SNS."""

    @pytest.fixture
    def submission_service_with_mocks(self):
        """Create SlangSubmissionService with all dependencies mocked."""
        from services.slang_submission_service import SlangSubmissionService

        with patch(
            "services.slang_submission_service.SlangSubmissionRepository"
        ) as mock_repo_class:
            with patch(
                "services.slang_submission_service.UserService"
            ) as mock_user_service_class:
                with patch(
                    "services.slang_submission_service.get_config_service"
                ) as mock_get_config:
                    with patch(
                        "services.slang_submission_service.aws_services"
                    ) as mock_aws_services:
                        # Setup mocks
                        mock_repo = Mock()
                        mock_repo.generate_submission_id.return_value = "sub_123"
                        mock_repo.create.return_value = "sub_123"
                        mock_repo.check_duplicate_submission.return_value = False
                        mock_repo_class.return_value = mock_repo

                        mock_user_service = Mock()
                        mock_user_service_class.return_value = mock_user_service

                        mock_config = Mock()
                        mock_submission_config = SlangSubmissionConfig(
                            submissions_topic_arn="arn:aws:sns:test:submissions",
                            validation_request_topic_arn="arn:aws:sns:test:validation",
                        )
                        mock_config.get_config.return_value = mock_submission_config
                        mock_get_config.return_value = mock_config

                        mock_sns = Mock()
                        mock_aws_services.sns_client = mock_sns

                        service = SlangSubmissionService()
                        service.repository = mock_repo
                        service.user_service = mock_user_service
                        service.sns_client = mock_sns

                        yield service

    def test_submit_slang_publishes_to_validation_topic(
        self, submission_service_with_mocks
    ):
        """Test submit_slang publishes validation request to SNS."""
        from models.slang import SlangSubmissionRequest

        request = SlangSubmissionRequest(
            slang_term="bussin",
            meaning="Really good",
            example_usage="That pizza was bussin!",
            context=SubmissionContext.MANUAL,
        )

        # Mock rate limit check and premium check to pass
        submission_service_with_mocks._check_rate_limit = Mock(return_value=True)
        submission_service_with_mocks._is_premium_user = Mock(return_value=True)

        # Submit slang
        response = submission_service_with_mocks.submit_slang(request, "user_123")

        # Verify SNS publish was called
        assert submission_service_with_mocks.sns_client.publish.called

        # Verify message structure
        call_args = submission_service_with_mocks.sns_client.publish.call_args
        assert call_args[1]["TopicArn"] == "arn:aws:sns:test:validation"
        message = json.loads(call_args[1]["Message"])
        assert message["slang_term"] == "bussin"
        assert "submission_id" in message
        assert "user_id" in message

    def test_submit_slang_returns_immediately(self, submission_service_with_mocks):
        """Test submit_slang returns immediately without blocking on validation."""
        from models.slang import SlangSubmissionRequest

        request = SlangSubmissionRequest(
            slang_term="bussin",
            meaning="Really good",
            example_usage="That pizza was bussin!",
            context=SubmissionContext.MANUAL,
        )

        submission_service_with_mocks._check_rate_limit = Mock(return_value=True)
        submission_service_with_mocks._is_premium_user = Mock(return_value=True)

        # Submit should return immediately
        response = submission_service_with_mocks.submit_slang(request, "user_123")

        # Verify response is PENDING (not APPROVED or REJECTED)
        assert response.status == ApprovalStatus.PENDING
        assert "checking it out now" in response.message.lower()


class TestValidationServiceAttributes:
    """Test validation service uses correct attributes."""

    def test_fallback_validation_requires_submission_parameter(self):
        """Test _fallback_validation requires submission parameter."""
        from services.slang_validation_service import SlangValidationService

        submission = SlangSubmission(
            submission_id="sub_123",
            user_id="user_456",
            slang_term="test",
            meaning="test meaning",
            example_usage="test usage",
            context=SubmissionContext.MANUAL,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            upvotes=0,
            upvoted_by=[],
        )

        with patch(
            "services.slang_validation_service.get_config_service"
        ) as mock_get_config:
            with patch("services.slang_validation_service.aws_services"):
                mock_config = Mock()
                mock_get_config.return_value = mock_config

                service = SlangValidationService()

                # This should not raise an error
                result = service._fallback_validation(submission)

                assert result.is_valid is True
                assert result.confidence == Decimal("0.5")
                assert result.usage_score == 5
