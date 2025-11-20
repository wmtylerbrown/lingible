from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from models.translations import TranslationDirection, TranslationHistory
from repositories.translation_repository import (
    QueryResult,
    TranslationRepository,
)


def build_translation(
    user_id: str,
    translation_id: str,
    *,
    created_at: datetime,
    confidence: Decimal | None = None,
) -> TranslationHistory:
    return TranslationHistory(
        translation_id=translation_id,
        user_id=user_id,
        original_text="hello world",
        translated_text="sup world",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        confidence_score=confidence,
        created_at=created_at,
        model_used="bedrock",
    )


def test_create_and_get_translation_round_trip(translations_table: str) -> None:
    repository = TranslationRepository()

    created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    translation = build_translation(
        user_id="user-123",
        translation_id="trans-abc",
        created_at=created_at,
        confidence=Decimal("0.85"),
    )

    assert repository.create_translation(translation) is True

    fetched = repository.get_translation("user-123", "trans-abc")
    assert fetched is not None
    assert fetched.translation_id == translation.translation_id
    assert fetched.user_id == translation.user_id
    assert fetched.direction is TranslationDirection.ENGLISH_TO_GENZ
    assert fetched.confidence_score == Decimal("0.85")
    assert fetched.created_at == created_at
    assert fetched.model_used == "bedrock"


def test_get_user_translations_applies_limit_and_sort(translations_table: str) -> None:
    repository = TranslationRepository()

    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    translations = [
        build_translation(
            user_id="user-123",
            translation_id=f"trans-{index}",
            created_at=base_time + timedelta(minutes=index),
        )
        for index in range(3)
    ]

    for translation in translations:
        assert repository.create_translation(translation) is True

    result = repository.get_user_translations("user-123", limit=2)
    assert isinstance(result, QueryResult)
    assert len(result.items) == 2
    # Results are returned latest-first
    returned_ids = [item.translation_id for item in result.items]
    assert returned_ids == ["trans-2", "trans-1"]
    assert result.last_evaluated_key is not None
    assert result.count == 2


def test_delete_translation_handles_missing_and_existing_records(
    translations_table: str,
) -> None:
    repository = TranslationRepository()

    # Missing translation returns False without raising
    assert repository.delete_translation("user-123", "does-not-exist") is False

    translation = build_translation(
        user_id="user-123",
        translation_id="trans-delete",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert repository.create_translation(translation) is True

    assert repository.delete_translation("user-123", "trans-delete") is True
    assert repository.get_translation("user-123", "trans-delete") is None


def test_get_user_translations_paginates(translations_table: str) -> None:
    repository = TranslationRepository()

    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(5):
        translation = build_translation(
            user_id="user-abc",
            translation_id=f"trans-{index}",
            created_at=base_time + timedelta(minutes=index),
        )
        assert repository.create_translation(translation)

    first_page: QueryResult[TranslationHistory] = repository.get_user_translations(
        "user-abc", limit=2
    )
    assert len(first_page.items) == 2
    assert first_page.last_evaluated_key is not None

    second_page = repository.get_user_translations(
        "user-abc", limit=2, last_evaluated_key=first_page.last_evaluated_key
    )
    assert len(second_page.items) == 2
    returned_ids = [item.translation_id for item in first_page.items + second_page.items]
    assert returned_ids == ["trans-4", "trans-3", "trans-2", "trans-1"]


def test_delete_user_translations_counts_deletions(translations_table: str) -> None:
    repository = TranslationRepository()
    for index in range(3):
        assert repository.create_translation(
            build_translation(
                user_id="bulk-user",
                translation_id=f"bulk-{index}",
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            )
        )

    deleted = repository.delete_translation("bulk-user", "bulk-0")
    assert deleted is True
    remaining = repository.get_user_translations("bulk-user")
    assert len(remaining.items) == 2


def test_delete_translation_returns_false_when_missing(translations_table: str) -> None:
    repository = TranslationRepository()
    assert repository.delete_translation("user-xyz", "missing") is False


def test_get_user_translations_returns_query_result_structure(translations_table: str) -> None:
    repository = TranslationRepository()

    result = repository.get_user_translations("nobody")
    assert isinstance(result, QueryResult)
    assert result.count == 0
    assert result.items == []
    assert result.last_evaluated_key is None


def test_generate_translation_id_returns_uuid(translations_table: str) -> None:
    repository = TranslationRepository()
    translation_id = repository.generate_translation_id()
    assert len(translation_id) == 36  # standard UUID string length


def test_create_translation_handles_exception(
    translations_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = TranslationRepository()
    translation = build_translation(
        user_id="user-err",
        translation_id="trans-err",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    def raise_put(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    assert repository.create_translation(translation) is False


def test_get_translation_handles_exception(
    translations_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = TranslationRepository()

    def raise_get(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get)
    assert repository.get_translation("user", "bad") is None


def test_get_user_translations_handles_exception(
    translations_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = TranslationRepository()

    def raise_query(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    result = repository.get_user_translations("user")
    assert result.items == []
    assert result.count == 0


def test_delete_translation_handles_delete_errors(
    translations_table: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = TranslationRepository()
    existing = build_translation(
        user_id="user-del",
        translation_id="trans-del",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(repository, "get_translation", lambda *_: existing)

    def raise_delete(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "delete_item", raise_delete)
    assert repository.delete_translation("user-del", "trans-del") is False
