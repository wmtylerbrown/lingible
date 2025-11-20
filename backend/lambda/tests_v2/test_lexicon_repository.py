from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from models.quiz import QuizCategory, QuizDifficulty
from models.slang import ApprovalStatus, SlangTerm
from repositories.lexicon_repository import LexiconRepository
from utils.aws_services import aws_services


def make_term(term: str = "rizz") -> SlangTerm:
    return SlangTerm(
        term=term,
        gloss="charisma",
        meaning="charisma or appeal",
        examples=["He has rizz."],
        tags=["popular"],
        category="general",
        quiz_category=QuizCategory.SOCIAL,
        quiz_difficulty=QuizDifficulty.BEGINNER,
        is_quiz_eligible=True,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        confidence=Decimal("0.9"),
        momentum=1.0,
    )


def test_create_and_get_term_round_trip(lexicon_table: str) -> None:
    repository = LexiconRepository()
    term = make_term()

    assert repository.save_lexicon_term(term)

    fetched = repository.get_term_by_slang("rizz")
    assert fetched is not None
    assert fetched.term == "rizz"
    assert fetched.quiz_category is QuizCategory.SOCIAL
    # Verify float fields are float (not Decimal) when read from DB
    assert isinstance(fetched.confidence, float), "confidence should be float after DB read"
    assert isinstance(fetched.momentum, float), "momentum should be float after DB read"


def test_get_terms_by_category_uses_index(lexicon_table: str) -> None:
    repository = LexiconRepository()
    assert repository.save_lexicon_term(make_term("based"))
    assert repository.save_lexicon_term(make_term("mid"))

    results = repository.get_terms_by_category(QuizCategory.SOCIAL, limit=5)
    assert {term.term for term in results} == {"based", "mid"}


def test_get_quiz_eligible_terms_by_difficulty(lexicon_table: str) -> None:
    repository = LexiconRepository()
    beginner = make_term("yeet")
    intermediate = make_term("sus")
    intermediate.quiz_difficulty = QuizDifficulty.INTERMEDIATE
    assert repository.save_lexicon_term(beginner)
    assert repository.save_lexicon_term(intermediate)

    beginner_terms = repository.get_quiz_eligible_terms(QuizDifficulty.BEGINNER, limit=10)
    assert [term.term for term in beginner_terms] == ["yeet"]


def test_update_quiz_statistics_increments_fields(lexicon_table: str) -> None:
    repository = LexiconRepository()
    term = make_term()
    assert repository.save_lexicon_term(term)

    repository.update_quiz_statistics(term.slang_term, is_correct=True)
    repository.update_quiz_statistics(term.slang_term, is_correct=False)

    updated = repository.get_term_by_slang(term.slang_term)
    assert updated is not None
    assert updated.times_in_quiz == 2
    assert 0.0 <= (updated.quiz_accuracy_rate or 0.0) <= 1.0


def test_get_all_lexicon_terms_returns_all_entries(lexicon_table: str) -> None:
    repository = LexiconRepository()
    assert repository.save_lexicon_term(make_term("alpha"))
    assert repository.save_lexicon_term(make_term("beta"))

    terms = repository.get_all_lexicon_terms()
    assert {term.term for term in terms} == {"alpha", "beta"}


def test_get_all_approved_terms_filters_status(lexicon_table: str) -> None:
    repository = LexiconRepository()
    approved = make_term("approved")
    rejected = make_term("rejected").model_copy(update={"status": ApprovalStatus.REJECTED})
    assert repository.save_lexicon_term(approved)
    assert repository.save_lexicon_term(rejected)

    terms = repository.get_all_approved_terms()
    assert [term.term for term in terms] == ["approved"]


def test_mark_exported_updates_metadata(lexicon_table: str) -> None:
    repository = LexiconRepository()
    term = make_term("exportable")
    assert repository.save_lexicon_term(term)

    repository.mark_exported(term.slang_term, "s3://bucket")

    table = aws_services.get_table(lexicon_table)
    key = {"PK": repository._term_pk(term.slang_term), "SK": repository._lexicon_sk()}
    item = table.get_item(Key=key)["Item"]
    assert item["last_exported_source"] == "s3://bucket"
    assert "last_exported_at" in item


def test_get_quiz_eligible_terms_excludes_requested_terms(lexicon_table: str) -> None:
    repository = LexiconRepository()
    finalist = make_term("finalist").model_copy(update={"confidence": Decimal("0.95")})
    other = make_term("other").model_copy(update={"confidence": Decimal("0.5")})
    assert repository.save_lexicon_term(finalist)
    assert repository.save_lexicon_term(other)

    results = repository.get_quiz_eligible_terms(
        QuizDifficulty.BEGINNER, limit=5, exclude_terms=["finalist"]
    )
    assert [term.term for term in results] == ["other"]


def test_get_terms_by_category_handles_exception(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_terms_by_category(QuizCategory.GENERAL) == []


def test_update_quiz_statistics_noop_when_missing(lexicon_table: str) -> None:
    repository = LexiconRepository()
    # Should not raise even if term does not exist
    repository.update_quiz_statistics("missing-term", is_correct=True)


def test_wrong_answer_pool_round_trip(lexicon_table: str) -> None:
    repository = LexiconRepository()
    assert repository.create_wrong_answer_pool("social", ["yeet", "sus"]) is True

    pool = repository.get_wrong_answer_pool("social")
    assert pool == ["yeet", "sus"]


def test_wrong_answer_pool_handles_errors(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_get_item(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    def raise_put_item(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get_item)
    assert repository.get_wrong_answer_pool("bad") is None

    monkeypatch.setattr(repository.table, "put_item", raise_put_item)
    assert repository.create_wrong_answer_pool("bad", ["one"]) is False


def test_save_lexicon_term_handles_exception(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()
    term = make_term("failing")

    def raise_put(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    assert repository.save_lexicon_term(term) is False


def test_item_to_slang_term_handles_invalid_payload(lexicon_table: str) -> None:
    repository = LexiconRepository()
    bad_item = {"term": "oops", "status": "not-a-status"}
    assert repository._item_to_slang_term(bad_item) is None


def test_get_all_lexicon_terms_handles_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_all_lexicon_terms() == []


def test_get_term_by_slang_handles_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_term_by_slang("unknown") is None


def test_get_all_approved_terms_handles_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_scan(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "scan", raise_scan)
    assert repository.get_all_approved_terms() == []


def test_mark_exported_handles_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    repository.mark_exported("term", "source")  # Should not raise


def test_get_quiz_eligible_terms_handles_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()

    def raise_query(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_quiz_eligible_terms(QuizDifficulty.BEGINNER) == []


def test_update_quiz_statistics_handles_update_error(
    lexicon_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LexiconRepository()
    term = make_term("stats-term")
    assert repository.save_lexicon_term(term)

    def raise_update(*_: Any, **__: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    repository.update_quiz_statistics(term.slang_term, is_correct=True)
