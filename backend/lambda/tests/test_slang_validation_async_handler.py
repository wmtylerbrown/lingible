"""Tests for slang validation async handler."""

import pytest
import json
from unittest.mock import Mock, patch
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
        from handlers.slang_validation_async.handler import handler

        # Mock dependencies
        with patch(
            "handlers.slang_validation_async.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_async.handler.SlangSubmissionService"
            ) as mock_submission_service_class:
                with patch(
                    "handlers.slang_validation_async.handler.SubmissionsRepository"
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
                    result = handler(sample_validation_event, Mock())

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
        from handlers.slang_validation_async.handler import handler

        with patch(
            "handlers.slang_validation_async.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_async.handler.SlangSubmissionService"
            ) as mock_submission_service_class:
                with patch(
                    "handlers.slang_validation_async.handler.SubmissionsRepository"
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
                    result = handler(sample_validation_event, Mock())

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
        from handlers.slang_validation_async.handler import handler

        with patch(
            "handlers.slang_validation_async.handler.SlangValidationService"
        ):
            with patch(
                "handlers.slang_validation_async.handler.SlangSubmissionService"
            ):
                with patch(
                    "handlers.slang_validation_async.handler.SubmissionsRepository"
                ) as mock_repo_class:
                    mock_repo = Mock()
                    mock_repo.get_submission_by_id.return_value = None
                    mock_repo_class.return_value = mock_repo

                    result = handler(sample_validation_event, Mock())

                    assert result["statusCode"] == 404
                    body = json.loads(result["body"])
                    assert "not found" in body["error"].lower()

    def test_handler_validation_failure_uses_fallback(
        self, sample_validation_event, sample_submission
    ):
        """Test handler uses fallback validation on error."""
        from handlers.slang_validation_async.handler import handler

        fallback_result = LLMValidationResult(
            is_valid=True,
            confidence=Decimal("0.5"),
            evidence=[],
            recommended_definition=None,
            usage_score=5,
            validated_at=datetime.now(timezone.utc),
        )

        with patch(
            "handlers.slang_validation_async.handler.SlangValidationService"
        ) as mock_validation_service_class:
            with patch(
                "handlers.slang_validation_async.handler.SlangSubmissionService"
            ):
                with patch(
                    "handlers.slang_validation_async.handler.SubmissionsRepository"
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
                    result = handler(sample_validation_event, Mock())

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
