from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from models.trending import TrendingCategory, TrendingTerm
from repositories.trending_repository import TrendingRepository


def make_term(term: str, *, active: bool = True, category: TrendingCategory = TrendingCategory.SLANG, popularity: Decimal = Decimal("42.5")) -> TrendingTerm:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return TrendingTerm(
        term=term,
        definition=f"Definition for {term}",
        category=category,
        popularity_score=popularity,
        search_count=100,
        translation_count=50,
        first_seen=now - timedelta(days=7),
        last_updated=now,
        is_active=active,
        example_usage=f"Example usage of {term}",
        origin="internet",
        related_terms=["alt"],
    )


def test_create_and_get_trending_term_round_trip(trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("rizzmeter", popularity=Decimal("77.7"))

    assert repository.create_trending_term(term) is True

    fetched = repository.get_trending_term("rizzmeter")
    assert fetched is not None
    assert fetched.term == term.term
    assert fetched.category is TrendingCategory.SLANG
    assert fetched.popularity_score == Decimal("77.7")
    assert fetched.example_usage == term.example_usage


def test_get_trending_terms_filters_active_and_category(trending_table: str) -> None:
    repository = TrendingRepository()
    assert repository.create_trending_term(make_term("term-active", active=True, category=TrendingCategory.EXPRESSION, popularity=Decimal("90")))
    assert repository.create_trending_term(make_term("term-inactive", active=False, category=TrendingCategory.EXPRESSION, popularity=Decimal("80")))
    assert repository.create_trending_term(make_term("term-hashtag", active=True, category=TrendingCategory.HASHTAG, popularity=Decimal("60")))

    active_terms = repository.get_trending_terms(category=TrendingCategory.EXPRESSION, active_only=True)
    names = {t.term for t in active_terms}
    assert names == {"term-active"}

    inactive_terms = repository.get_trending_terms(active_only=False)
    assert {t.term for t in inactive_terms} == {"term-inactive"}

    hashtag_terms = repository.get_trending_terms(category=TrendingCategory.HASHTAG)
    assert [t.term for t in hashtag_terms] == ["term-hashtag"]


def test_update_trending_term_mutates_existing(trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("lit", popularity=Decimal("50"))
    repository.create_trending_term(term)

    updated = term.model_copy(update={
        "definition": "Updated definition",
        "popularity_score": Decimal("70"),
        "is_active": False,
    })
    assert repository.update_trending_term(updated)

    fetched = repository.get_trending_term("lit")
    assert fetched is not None
    assert fetched.definition == "Updated definition"
    assert fetched.popularity_score == Decimal("70")
    assert fetched.is_active is False


def test_increment_search_count_updates_existing_term(trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("viral")
    repository.create_trending_term(term)

    assert repository.increment_search_count("viral") is True


def test_increment_translation_count_updates_existing_term(trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("mid")
    repository.create_trending_term(term)

    assert repository.increment_translation_count("mid") is True


def test_get_trending_stats_returns_counts() -> None:
    repository = TrendingRepository()
    repository.table = MagicMock()
    repository.table.query.side_effect = [
        {"Count": 5},
        {"Count": 2},
        {"Count": 1},
        {"Count": 1},
        {"Count": 1},
        {"Count": 0},
    ]

    stats = repository.get_trending_stats()
    assert stats["total_active_terms"] == 5
    assert all(isinstance(count, int) for count in stats["category_counts"].values())


def test_delete_trending_term_calls_delete(trending_table: str) -> None:
    repository = TrendingRepository()
    repository.table = MagicMock()

    assert repository.delete_trending_term("obsolete") is True
    repository.table.delete_item.assert_called_once()


def test_item_to_trending_term_parses_string_flags(trending_table: str) -> None:
    repository = TrendingRepository()
    now = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
    item = {
        "term": "inactive",
        "definition": "def",
        "category": TrendingCategory.SLANG.value,
        "popularity_score": "12.5",
        "search_count": 1,
        "translation_count": 1,
        "first_seen": now,
        "last_updated": now,
        "is_active": "ACTIVE#False",
    }
    term = repository._item_to_trending_term(item)
    assert term is not None
    assert term.is_active is False


def test_item_to_trending_term_handles_missing_fields(trending_table: str) -> None:
    repository = TrendingRepository()
    assert repository._item_to_trending_term({"term": "oops"}) is None


def test_get_trending_terms_fetches_full_items(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()
    assert repository.create_trending_term(make_term("full"))

    def fake_query(*_: object, **__: object) -> dict[str, list[dict[str, str]]]:
        return {
            "Items": [
                {
                    "PK": "TERM#full",
                    "SK": "METADATA#trending",
                    "category": TrendingCategory.SLANG.value,
                    "is_active": "ACTIVE#True",
                }
            ]
        }

    monkeypatch.setattr(repository.table, "query", fake_query)
    terms = repository.get_trending_terms(category=TrendingCategory.SLANG, active_only=False)
    assert [term.term for term in terms] == ["full"]


def test_get_trending_terms_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()

    def raise_query(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    assert repository.get_trending_terms() == []


def test_increment_search_count_returns_false_for_missing(trending_table: str) -> None:
    repository = TrendingRepository()
    assert repository.increment_search_count("missing") is False


def test_increment_translation_count_returns_false_for_missing(trending_table: str) -> None:
    repository = TrendingRepository()
    assert repository.increment_translation_count("missing") is False


def test_get_trending_stats_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()

    def raise_query(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "query", raise_query)
    stats = repository.get_trending_stats()
    assert stats["total_active_terms"] == 0
    assert stats["category_counts"] == {}


def test_delete_trending_term_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()

    def raise_delete(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "delete_item", raise_delete)
    assert repository.delete_trending_term("term") is False


def test_create_trending_term_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("error-term")

    def raise_put(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    assert repository.create_trending_term(term) is False


def test_get_trending_term_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()

    def raise_get(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "get_item", raise_get)
    assert repository.get_trending_term("boom") is None


def test_update_trending_term_handles_error(monkeypatch: pytest.MonkeyPatch, trending_table: str) -> None:
    repository = TrendingRepository()
    term = make_term("update-error")

    def raise_put(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "put_item", raise_put)
    assert repository.update_trending_term(term) is False


def test_increment_search_count_handles_update_error(
    monkeypatch: pytest.MonkeyPatch, trending_table: str
) -> None:
    repository = TrendingRepository()
    existing = make_term("search-error")
    repository.get_trending_term = lambda *_: existing  # type: ignore[assignment]

    def raise_update(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert repository.increment_search_count("search-error") is False


def test_increment_translation_count_handles_update_error(
    monkeypatch: pytest.MonkeyPatch, trending_table: str
) -> None:
    repository = TrendingRepository()
    existing = make_term("translation-error")
    repository.get_trending_term = lambda *_: existing  # type: ignore[assignment]

    def raise_update(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(repository.table, "update_item", raise_update)
    assert repository.increment_translation_count("translation-error") is False
