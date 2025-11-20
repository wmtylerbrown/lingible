from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

import pytest

from models.slang import (
    ApprovalStatus,
    ApprovalType,
    SlangSubmission,
    SlangSubmissionStatus,
    SubmissionContext,
    LLMValidationResult,
    LLMValidationEvidence,
)
from repositories.submissions_repository import SubmissionsRepository


def make_submission(
    submission_id: str = "sub_001",
    *,
    slang_term: str = "rizz",
    status: ApprovalStatus = ApprovalStatus.PENDING,
    created_at: datetime | None = None,
    llm_validation_status: SlangSubmissionStatus = SlangSubmissionStatus.PENDING_VALIDATION,
    llm_confidence_score: Decimal | None = None,
    upvotes: int = 0,
    upvoted_by: list[str] | None = None,
) -> SlangSubmission:
    now = created_at or datetime(2025, 1, 1, tzinfo=timezone.utc)
    return SlangSubmission(
        submission_id=submission_id,
        user_id="user-123",
        slang_term=slang_term,
        meaning="charisma",
        example_usage="He has serious rizz.",
        context=SubmissionContext.MANUAL,
        original_translation_id=None,
        status=status,
        created_at=now,
        reviewed_at=None,
        reviewed_by=None,
        llm_validation_status=llm_validation_status,
        llm_confidence_score=llm_confidence_score,
        llm_validation_result=None,
        approval_type=None,
        approved_by=None,
        upvotes=upvotes,
        upvoted_by=upvoted_by or [],
    )


def test_create_and_get_submission_round_trip(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()

    assert repository.create_submission(submission)

    fetched = repository.get_submission_by_id(submission.submission_id)
    assert fetched is not None
    assert fetched.slang_term == "rizz"
    assert fetched.status is ApprovalStatus.PENDING


def test_get_submissions_by_status_uses_index(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    assert repository.create_submission(make_submission("sub_pending"))
    approved = make_submission(
        "sub_approved", status=ApprovalStatus.APPROVED, slang_term="based"
    )
    assert repository.create_submission(approved)

    pending = repository.get_submissions_by_status(
    ApprovalStatus.PENDING, limit=10)
    assert {sub.submission_id for sub in pending} == {"sub_pending"}


def test_get_user_submissions_returns_sorted(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    first = make_submission("sub1")
    second = make_submission("sub2")
    second.created_at = first.created_at + timedelta(minutes=5)
    assert repository.create_submission(first)
    assert repository.create_submission(second)

    submissions = repository.get_user_submissions("user-123", limit=10)
    ids = [sub.submission_id for sub in submissions]
    assert ids == ["sub2", "sub1"]


def test_update_validation_result_persists_data(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()
    assert repository.create_submission(submission)

    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.91"),
        evidence=[LLMValidationEvidence(source="web", example="usage")],
        recommended_definition="cool",
        usage_score=7,
        validated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    assert repository.update_validation_result(submission.submission_id, submission.user_id, result)

    fetched = repository.get_submission_by_id(submission.submission_id)
    assert fetched is not None
    assert fetched.llm_validation_result is not None
    assert fetched.llm_validation_result.confidence == Decimal("0.91")


def test_update_approval_status_updates_status_and_metadata(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()
    assert repository.create_submission(submission)

    assert repository.update_approval_status(
        submission.submission_id,
        submission.user_id,
        SlangSubmissionStatus.ADMIN_APPROVED,
        ApprovalType.ADMIN_MANUAL,
    )

    updated = repository.get_submission_by_id(submission.submission_id)
    assert updated is not None
    assert updated.status is ApprovalStatus.APPROVED
    assert updated.approval_type is ApprovalType.ADMIN_MANUAL


def test_create_submission_returns_false_on_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()

    def raise_put(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    assert repository.create_submission(submission) is False


def test_get_pending_submissions_returns_pending(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    repo_pending = make_submission("pending-one")
    repo_approved = make_submission(
        "approved-one", status=ApprovalStatus.APPROVED, slang_term="based"
    )
    assert repository.create_submission(repo_pending)
    assert repository.create_submission(repo_approved)

    results = repository.get_pending_submissions(limit=5)
    assert [submission.submission_id for submission in results] == ["pending-one"]


def test_generate_submission_id_format(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    submission_id = repository.generate_submission_id()
    assert submission_id.startswith("sub_")
    assert len(submission_id) > 8


def test_get_validated_submissions_for_voting_filters(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    validated = make_submission(
        "sub_valid", llm_validation_status=SlangSubmissionStatus.VALIDATED
    )
    pending = make_submission(
        "sub_pending", llm_validation_status=SlangSubmissionStatus.PENDING_VALIDATION
    )
    assert repository.create_submission(validated)
    assert repository.create_submission(pending)

    results = repository.get_validated_submissions_for_voting(limit=5)
    assert len(results) == 1
    assert results[0].submission_id == "sub_valid"


def test_add_upvote_increments_and_tracks_voter(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    key_tracker: dict[str, Any] = {}

    monkeypatch.setattr(repository, "_get_key_for_submission", lambda _submission_id: {"PK": "TERM#rizz", "SK": "SUBMISSION#sub"})

    def capture_update(*_: Any, **kwargs: Any) -> None:
        key_tracker["kwargs"] = kwargs

    monkeypatch.setattr(repository.table, "update_item", capture_update)

    assert repository.add_upvote("sub_001", "user-123", "voter-1") is True
    expression_values = key_tracker["kwargs"]["ExpressionAttributeValues"]
    assert expression_values[":inc"] == 1
    assert expression_values[":voter"] == {"voter-1"}


def test_upvote_submission_returns_false_when_missing(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    assert repository.upvote_submission("missing", "voter") is False


def test_upvote_submission_uses_add_upvote(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()
    assert repository.create_submission(submission)

    called: dict[str, Any] = {}

    def fake_add(submission_id: str, user_id: str, voter_id: str) -> bool:
        called["args"] = (submission_id, user_id, voter_id)
        return True

    monkeypatch.setattr(repository, "add_upvote", fake_add)
    assert repository.upvote_submission(submission.submission_id, "voter-1") is True
    assert called["args"] == (submission.submission_id, submission.user_id, "voter-1")


def test_update_validation_result_returns_false_when_missing(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[],
        recommended_definition=None,
        usage_score=1,
        validated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    assert repository.update_validation_result("missing", "user-123", result) is False


def test_update_approval_status_returns_false_when_missing(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    assert (
        repository.update_approval_status(
            "missing",
            "user-123",
            SlangSubmissionStatus.ADMIN_APPROVED,
            ApprovalType.ADMIN_MANUAL,
        )
        is False
    )


def test_get_by_validation_status_handles_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)

    results = repository.get_by_validation_status(SlangSubmissionStatus.VALIDATED)
    assert results == []


def test_check_duplicate_submission_detects_recent(monkeypatch: pytest.MonkeyPatch, submissions_table: str) -> None:
    repository = SubmissionsRepository()

    def fake_query(*_: Any, **__: Any) -> dict[str, Any]:
        return {
            "Items": [
                {
                    "slang_term": "rizz",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

    monkeypatch.setattr(repository.table, "query", fake_query)
    assert repository.check_duplicate_submission("rizz", "user-123") is True


def test_check_duplicate_submission_returns_false_on_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.check_duplicate_submission("term", "user") is False


def test_get_user_submissions_handles_query_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_user_submissions("user-123") == []


def test_get_submission_by_id_returns_none_for_unknown(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    assert repository.get_submission_by_id("missing") is None


def test_update_validation_result_returns_false_when_serialization_none(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()
    assert repository.create_submission(submission)

    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[],
        recommended_definition=None,
        usage_score=1,
        validated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(repository, "_serialize_llm_result", lambda *_: None)
    assert (
        repository.update_validation_result(submission.submission_id, submission.user_id, result)
        is False
    )


def test_update_validation_result_handles_update_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    submission = make_submission()
    assert repository.create_submission(submission)
    result = LLMValidationResult(
        is_valid=True,
        confidence=Decimal("0.9"),
        evidence=[],
        recommended_definition=None,
        usage_score=1,
        validated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert (
        repository.update_validation_result(submission.submission_id, submission.user_id, result)
        is False
    )


def test_get_submissions_by_status_handles_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_submissions_by_status(ApprovalStatus.APPROVED) == []


def test_get_submission_by_id_handles_query_error(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_submission_by_id("any") is None


def test_add_upvote_returns_false_without_key(
    submissions_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubmissionsRepository()
    monkeypatch.setattr(repository, "_get_key_for_submission", lambda *_: None)
    assert repository.add_upvote("sub", "user", "voter") is False


def test_to_decimal_handles_invalid_input(submissions_table: str) -> None:
    repository = SubmissionsRepository()
    assert repository._to_decimal("not-a-number") is None
