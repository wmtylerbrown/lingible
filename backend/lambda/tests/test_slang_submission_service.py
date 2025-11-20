from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from models.config import SlangSubmissionConfig
from models.slang import (
    ApprovalStatus,
    ApprovalType,
    LLMValidationEvidence,
    LLMValidationResult,
    SlangSubmission,
    SlangSubmissionRequest,
    SlangSubmissionStatus,
    SubmissionContext,
    SlangSubmissionResponse,
    PendingSubmissionsResponse,
    UpvoteResponse,
    AdminApprovalResponse,
)
from models.users import UserTier
from services.slang_submission_service import SlangSubmissionService
from utils.exceptions import (
    BusinessLogicError,
    InsufficientPermissionsError,
    ResourceNotFoundError,
    ValidationError,
)
from utils.response import create_model_response


def _config() -> SlangSubmissionConfig:
    return SlangSubmissionConfig(
        submissions_topic_arn="arn:aws:sns:::submissions",
        validation_request_topic_arn="arn:aws:sns:::validation",
    )


def _request() -> SlangSubmissionRequest:
    return SlangSubmissionRequest(
        slang_term="rizz",
        meaning="charisma",
        example_usage="he's got rizz",
        context=SubmissionContext.MANUAL,
        translation_id=None,
    )


def _validation_result() -> LLMValidationResult:
    return LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.95"),
        evidence=[LLMValidationEvidence(source="web", example="usage")],
        recommended_definition="charm",
        usage_score=8,
        validated_at=datetime.now(timezone.utc),
    )


def _service() -> tuple[SlangSubmissionService, Mock, Mock, Mock, Mock]:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    service.repository = Mock()
    service.repository.check_duplicate_submission.return_value = False
    service.repository.get_user_submissions.return_value = []
    service.user_service = Mock()
    service.config_service = Mock()
    service.config_service.get_config.return_value = _config()
    service.submission_config = _config()
    service.sns_client = Mock()
    service.validation_service = Mock()
    service.validation_service.validate_submission.return_value = _validation_result()
    service.validation_service.determine_status.return_value = SlangSubmissionStatus.VALIDATED
    service.validation_service.should_auto_approve.return_value = True
    service._validate_submission = Mock()
    service._publish_validation_request = Mock()
    service._publish_submission_notification = Mock()
    service._publish_auto_approval_notification = Mock()
    return (
        service,
        service.repository,
        service.user_service,
        service.validation_service,
        service.sns_client,
    )


def test_submit_slang_happy_path() -> None:
    service, repository, user_service, validation_service, _sns = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.check_duplicate_submission.return_value = False
    repository.get_user_submissions.return_value = []
    repository.generate_submission_id.return_value = "sub_1"
    repository.create_submission.return_value = True
    repository.update_approval_status.return_value = True

    response = service.submit_slang(_request(), "user-1")

    assert response.status is ApprovalStatus.APPROVED
    repository.create_submission.assert_called_once()
    user_service.increment_slang_submitted.assert_called_once_with("user-1")
    validation_service.validate_submission.assert_called_once()


def test_submit_slang_requires_premium() -> None:
    service, _, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.FREE)
    with pytest.raises(InsufficientPermissionsError):
        service.submit_slang(_request(), "user-1")


def test_submit_slang_rejects_duplicates() -> None:
    service, repository, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.check_duplicate_submission.return_value = True
    with pytest.raises(ValidationError):
        service.submit_slang(_request(), "user-1")


def test_submit_slang_rate_limit() -> None:
    service, repository, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    now = datetime.now(timezone.utc)
    # 10 submissions in last 24h
    repository.get_user_submissions.return_value = [
        SlangSubmission(
            submission_id=str(i),
            user_id="user-1",
            slang_term="term",
            meaning="meaning",
            example_usage=None,
            context=SubmissionContext.MANUAL,
            original_translation_id=None,
            status=ApprovalStatus.PENDING,
            created_at=now - timedelta(hours=1),
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
        for i in range(10)
    ]

    with pytest.raises(BusinessLogicError):
        service.submit_slang(_request(), "user-1")


def test_submit_slang_handles_validation_rejection() -> None:
    service, repository, user_service, validation_service, _sns = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.generate_submission_id.return_value = "sub_2"
    repository.create_submission.return_value = True
    validation_service.should_auto_approve.return_value = False
    validation_service.determine_status.return_value = SlangSubmissionStatus.REJECTED

    response = service.submit_slang(_request(), "user-1")

    assert response.status is ApprovalStatus.REJECTED
    repository.update_approval_status.assert_called_with(
        "sub_2",
        "user-1",
        SlangSubmissionStatus.REJECTED,
        ApprovalType.LLM_AUTO,
    )


def test_submit_slang_routes_to_validation_queue() -> None:
    service, repository, user_service, validation_service, _sns = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.generate_submission_id.return_value = "sub_3"
    repository.create_submission.return_value = True
    validation_service.should_auto_approve.return_value = False
    validation_service.determine_status.return_value = SlangSubmissionStatus.VALIDATED

    response = service.submit_slang(_request(), "user-1")

    assert response.status is ApprovalStatus.PENDING
    service._publish_validation_request.assert_called_once()


def test_submit_slang_raises_when_repository_fails() -> None:
    service, repository, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.generate_submission_id.return_value = "sub_fail"
    repository.create_submission.return_value = False

    with pytest.raises(BusinessLogicError):
        service.submit_slang(_request(), "user-1")


def test_approve_submission_returns_false_when_missing() -> None:
    service, repository, _, _, _ = _service()
    repository.get_submission_by_id.return_value = None
    assert service.approve_submission("sub", "user", "admin") is False


def test_approve_submission_updates_status() -> None:
    service, repository, _, _, _ = _service()
    repository.get_submission_by_id.return_value = SlangSubmission(
        submission_id="sub",
        user_id="user-2",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    repository.update_approval_status.return_value = True
    assert service.approve_submission("sub", "user", "admin") is True
    repository.update_approval_status.assert_called_once_with(
        "sub", "user-2", SlangSubmissionStatus.ADMIN_APPROVED, ApprovalType.ADMIN_MANUAL
    )


def test_reject_submission_updates_status() -> None:
    service, repository, _, _, _ = _service()
    repository.get_submission_by_id.return_value = SlangSubmission(
        submission_id="sub",
        user_id="user-2",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    repository.update_approval_status.return_value = True
    assert service.reject_submission("sub", "user", "admin") is True
    repository.update_approval_status.assert_called_with(
        "sub", "user-2", SlangSubmissionStatus.REJECTED, ApprovalType.ADMIN_MANUAL
    )


def test_get_user_submissions_requires_premium() -> None:
    service, _, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.FREE)
    with pytest.raises(InsufficientPermissionsError):
        service.get_user_submissions("user-1")


def test_get_user_submissions_returns_list() -> None:
    service, repository, user_service, _, _ = _service()
    user_service.get_user.return_value = SimpleNamespace(tier=UserTier.PREMIUM)
    repository.get_user_submissions.return_value = ["sub"]
    assert service.get_user_submissions("user-1") == ["sub"]


def test_upvote_submission_happy_path() -> None:
    service, repository, _user_service, _validation_service, _sns = _service()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="owner",
        slang_term="term",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    updated_submission = submission.model_copy(update={"upvotes": 1})
    repository.get_submission_by_id.side_effect = [submission, updated_submission]
    repository.add_upvote.return_value = True

    response = service.upvote_submission("sub", "voter")

    assert response.upvotes == 1
    repository.add_upvote.assert_called_once_with("sub", "owner", "voter")


def test_upvote_submission_prevents_self_vote() -> None:
    service, repository, _user_service, _validation_service, _sns = _service()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="owner",
        slang_term="term",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    repository.get_submission_by_id.return_value = submission

    with pytest.raises(ValidationError):
        service.upvote_submission("sub", "owner")


def test_validate_submission_enforces_rules() -> None:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    bad_request = _request().model_copy(update={"meaning": "x" * 600})
    with pytest.raises(ValidationError):
        service._validate_submission(bad_request)


def test_check_rate_limit_allows_when_under() -> None:
    service, repository, _, _, _ = _service()
    repository.get_user_submissions.return_value = []
    assert service._check_rate_limit("user-1") is True


def test_check_rate_limit_fail_open_on_error() -> None:
    service, repository, _, _, _ = _service()
    repository.get_user_submissions.side_effect = RuntimeError("boom")
    assert service._check_rate_limit("user-1") is True


def test_publish_submission_notification_handles_exception() -> None:
    service, _, _, _, sns_client = _service()
    sns_client.publish.side_effect = RuntimeError("boom")
    submission = SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    service._publish_submission_notification(submission)


def test_publish_submission_notification_success() -> None:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    service.submission_config = _config()
    service.sns_client = Mock()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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

    service._publish_submission_notification(submission)
    service.sns_client.publish.assert_called_once()


def test_publish_auto_approval_notification_sends_message() -> None:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    service.submission_config = _config()
    service.sns_client = Mock()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
        status=ApprovalStatus.APPROVED,
        created_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by="system",
        llm_validation_status=SlangSubmissionStatus.AUTO_APPROVED,
        llm_confidence_score=Decimal("0.95"),
        llm_validation_result=None,
        approval_type=ApprovalType.LLM_AUTO,
        approved_by="system",
        upvotes=0,
        upvoted_by=[],
    )
    service._publish_auto_approval_notification(submission, _validation_result())
    service.sns_client.publish.assert_called_once()


def test_publish_validation_request_requires_topic() -> None:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    service.submission_config = _config().model_copy(
        update={"validation_request_topic_arn": None}
    )
    service.sns_client = Mock()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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

    service._publish_validation_request(submission)
    service.sns_client.publish.assert_not_called()


def test_publish_validation_request_sends_message() -> None:
    service = SlangSubmissionService.__new__(SlangSubmissionService)
    service.submission_config = _config()
    service.sns_client = Mock()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="user",
        slang_term="rizz",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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

    service._publish_validation_request(submission)
    service.sns_client.publish.assert_called_once()


def test_pending_submissions_response() -> None:
    service, repository, _, _, _ = _service()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="owner",
        slang_term="term",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
        status=ApprovalStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        reviewed_at=None,
        reviewed_by=None,
        llm_validation_status=SlangSubmissionStatus.VALIDATED,
        llm_confidence_score=None,
        llm_validation_result=None,
        approval_type=None,
        approved_by=None,
        upvotes=0,
        upvoted_by=[],
    )
    repository.get_by_validation_status.return_value = [submission, submission]
    response = service.get_pending_submissions(limit=2)
    assert response.total_count == 2
    assert response.has_more is True


def test_admin_approve_publishes_notification() -> None:
    service, repository, user_service, _, _ = _service()
    submission = SlangSubmission(
        submission_id="sub",
        user_id="owner",
        slang_term="term",
        meaning="meaning",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    repository.get_submission_by_id.return_value = submission
    repository.update_approval_status.return_value = True
    service._publish_approval_notification = Mock()

    response = service.admin_approve("sub", "admin-1")

    assert response.status is ApprovalStatus.APPROVED
    user_service.increment_slang_approved.assert_called_once_with("owner")
    service._publish_approval_notification.assert_called_once_with(submission)


def test_admin_reject_handles_missing_submission() -> None:
    service, repository, _, _, _ = _service()
    repository.get_submission_by_id.return_value = None
    with pytest.raises(ResourceNotFoundError):
        service.admin_reject("missing", "admin")


def test_service_init_sets_dependencies() -> None:
    with patch(
        "services.slang_submission_service.SubmissionsRepository"
    ) as repo_cls, patch(
        "services.slang_submission_service.UserService"
    ) as user_cls, patch(
        "services.slang_submission_service.get_config_service"
    ) as config_fn, patch(
        "services.slang_submission_service.SlangValidationService"
    ) as validation_cls:
        config = Mock()
        config.get_config.return_value = _config()
        config_fn.return_value = config
        repo_cls.return_value = Mock()
        user_cls.return_value = Mock()
        validation_cls.return_value = Mock()

        service = SlangSubmissionService()

        assert service.repository is repo_cls.return_value
        assert service.user_service is user_cls.return_value
        assert service.validation_service is validation_cls.return_value


def test_slang_submission_response_serialization_matches_api_contract() -> None:
    response = SlangSubmissionResponse(
        submission_id="sub-abc",
        status=ApprovalStatus.PENDING,
        message="Thanks for your submission!",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["submission_id"] == "sub-abc"
    assert body["status"] == ApprovalStatus.PENDING.value
    datetime.fromisoformat(body["created_at"])


def test_pending_submissions_response_serialization_matches_api_contract() -> None:
    submission = SlangSubmission(
        submission_id="sub-1",
        user_id="user-1",
        slang_term="rizz",
        meaning="charisma",
        example_usage=None,
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
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
    response = PendingSubmissionsResponse(
        submissions=[submission],
        total_count=1,
        has_more=False,
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["total_count"] == 1
    assert body["has_more"] is False
    assert body["submissions"][0]["slang_term"] == "rizz"


def test_upvote_response_serialization_matches_api_contract() -> None:
    response = UpvoteResponse(
        submission_id="sub-88",
        upvotes=5,
        message="Upvote recorded",
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["submission_id"] == "sub-88"
    assert body["upvotes"] == 5
    assert body["message"] == "Upvote recorded"


def test_admin_approval_response_serialization_matches_api_contract() -> None:
    response = AdminApprovalResponse(
        submission_id="sub-approve",
        status=ApprovalStatus.APPROVED,
        message="Approved",
    )

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["submission_id"] == "sub-approve"
    assert body["status"] == ApprovalStatus.APPROVED.value
def test_is_premium_user_handles_exception() -> None:
    service, _, user_service, _, _ = _service()
    user_service.get_user.side_effect = RuntimeError("boom")
    assert service._is_premium_user("user-1") is False
