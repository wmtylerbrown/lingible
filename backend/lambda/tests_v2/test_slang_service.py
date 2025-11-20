from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from models.config import LLMConfig
from models.slang import AgeFilterMode, AgeRating, SlangTranslationResponse
from services.slang_service import SlangService


@pytest.fixture
def dummy_config() -> LLMConfig:
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


def _build_translation_response(text: str = "translated") -> SlangTranslationResponse:
    return SlangTranslationResponse(
        translated=text,
        confidence=Decimal("0.9"),
        applied_terms=["term"],
    )


def test_translate_to_english_happy_path(dummy_config: LLMConfig) -> None:
    with patch("services.slang_service.get_config_service") as config_service_cls, \
         patch("services.slang_service.SlangLexiconService") as lex_cls, \
         patch("services.slang_service.SlangMatchingService") as match_cls, \
         patch("services.slang_service.SlangLLMService") as llm_cls:

        config_service = config_service_cls.return_value
        config_service.get_config.return_value = dummy_config

        lex_service = lex_cls.return_value
        lex_service.load_lexicon.return_value = SimpleNamespace(items=["term"])

        match_service = match_cls.return_value
        match_service.build_automaton.return_value = "automaton"
        match_service.match_lexicon.return_value = ["span"]

        llm_service = llm_cls.return_value
        llm_service.translate_with_context.return_value = _build_translation_response()

        service = SlangService()
        response = service.translate_to_english("w text")

    assert response.translated == "translated"
    lex_service.load_lexicon.assert_called_once()
    match_service.build_automaton.assert_called_once()
    match_service.match_lexicon.assert_called_once_with("w text".lower(), "automaton")
    llm_service.translate_with_context.assert_called_once()


def test_translate_to_english_requires_lexicon(dummy_config: LLMConfig) -> None:
    with patch("services.slang_service.get_config_service") as config_service_cls, \
         patch("services.slang_service.SlangLexiconService") as lex_cls, \
         patch("services.slang_service.SlangMatchingService"), \
         patch("services.slang_service.SlangLLMService"):

        config_service = config_service_cls.return_value
        config_service.get_config.return_value = dummy_config

        lex_service = lex_cls.return_value
        lex_service.load_lexicon.return_value = None

        service = SlangService()
        with pytest.raises(ValueError):
            service.translate_to_english("text")


def test_translate_to_genz_delegates_to_llm(dummy_config: LLMConfig) -> None:
    with patch("services.slang_service.get_config_service") as config_service_cls, \
         patch("services.slang_service.SlangLexiconService"), \
         patch("services.slang_service.SlangMatchingService"), \
         patch("services.slang_service.SlangLLMService") as llm_cls:

        config_service = config_service_cls.return_value
        config_service.get_config.return_value = dummy_config
        llm_service = llm_cls.return_value
        llm_service.translate_to_genz.return_value = _build_translation_response("genz")

        service = SlangService()
        response = service.translate_to_genz("hello")

    llm_service.translate_to_genz.assert_called_once_with("hello")
    assert response.translated == "genz"
