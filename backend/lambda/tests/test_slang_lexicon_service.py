from __future__ import annotations

import io
import json
from datetime import datetime
from unittest.mock import mock_open, patch

import pytest

from models.config import LLMConfig
from models.slang import AgeFilterMode, AgeRating, SlangLexicon, SlangTerm
from services.slang_lexicon_service import SlangLexiconService


def _make_config() -> LLMConfig:
    return LLMConfig(
        lexicon_s3_bucket="bucket",
        lexicon_s3_key="key",
        model="model",
        max_tokens=1000,
        temperature=0.5,
        top_p=0.95,
        low_confidence_threshold=0.5,
        age_max_rating=AgeRating.EVERYONE,
        age_filter_mode=AgeFilterMode.SKIP,
    )


def _make_term(term: str = "rizz", confidence: float = 0.9, age_rating: AgeRating = AgeRating.EVERYONE) -> SlangTerm:
    return SlangTerm(
        term=term,
        gloss="charisma",
        variants=[term, f"{term}y"],
        tags=["popular"],
        examples=[f"use of {term}"],
        confidence=confidence,
        age_rating=age_rating,
        categories=["social"],
    )


def _lexicon_payload() -> dict:
    lexicon = SlangLexicon(
        version="1.0",
        generated_at=datetime.now().isoformat(),
        count=1,
        items=[_make_term()],
    )
    return lexicon.model_dump(mode="json")


def test_load_lexicon_from_s3() -> None:
    config = _make_config()
    payload = json.dumps(_lexicon_payload())
    fake_body = io.BytesIO(payload.encode("utf-8"))

    with patch("services.slang_lexicon_service.aws_services") as aws_services_mock:
        aws_services_mock.s3_client.get_object.return_value = {"Body": fake_body}
        service = SlangLexiconService(config)
        lexicon = service.load_lexicon()

    assert lexicon.count == 1
    aws_services_mock.s3_client.get_object.assert_called_once_with(
        Bucket="bucket", Key="key"
    )


def test_load_lexicon_uses_cache_after_first_call() -> None:
    config = _make_config()
    payload = json.dumps(_lexicon_payload())
    fake_body = io.BytesIO(payload.encode("utf-8"))

    with patch("services.slang_lexicon_service.aws_services") as aws_services_mock:
        aws_services_mock.s3_client.get_object.return_value = {"Body": fake_body}
        service = SlangLexiconService(config)
        service.load_lexicon()
        service.load_lexicon()

    assert aws_services_mock.s3_client.get_object.call_count == 1


def test_load_lexicon_fallback_to_file(tmp_path) -> None:
    config = _make_config()
    payload = json.dumps(_lexicon_payload())

    fallback_file = tmp_path / "lexicon.json"
    fallback_file.write_text(payload)

    with patch("services.slang_lexicon_service.aws_services") as aws_services_mock, \
         patch("services.slang_lexicon_service.os.path.join", return_value=str(fallback_file)), \
         patch("builtins.open", mock_open(read_data=payload)) as open_mock:

        aws_services_mock.s3_client.get_object.side_effect = RuntimeError("boom")
        service = SlangLexiconService(config)
        lexicon = service.load_lexicon()

    assert lexicon.count == 1
    open_mock.assert_called()


def test_getters_filter_terms() -> None:
    config = _make_config()
    service = SlangLexiconService(config)
    service._lexicon = SlangLexicon(
        version="1.0",
        generated_at=datetime.now().isoformat(),
        count=2,
        items=[
            _make_term("rizz", confidence=0.95, age_rating=AgeRating.EVERYONE),
            _make_term("griddy", confidence=0.2, age_rating=AgeRating.MATURE_18),
        ],
    )

    assert service.get_terms_by_confidence(0.9)[0].term == "rizz"
    assert service.get_terms_by_age_rating("T16")[0].term == "rizz"
    assert service.get_terms_by_category("social")[0].term == "rizz"

    results = service.search_terms("gridd")
    assert results[0].term == "griddy"

    exact = service.search_terms("griddy", exact_match=True)
    assert exact[0].term == "griddy"


def test_variant_mapping_and_lookup() -> None:
    config = _make_config()
    service = SlangLexiconService(config)
    term = _make_term("yeet")
    service._lexicon = SlangLexicon(
        version="1.0",
        generated_at=datetime.now().isoformat(),
        count=1,
        items=[term],
    )

    mapping = service.get_variant_mapping()
    assert "yeet" in mapping
    assert mapping["yeet"][0][0].term == "yeet"

    found = service.get_term_by_canonical("YEET")
    assert found.term == "yeet"
