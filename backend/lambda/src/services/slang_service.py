"""Unified slang translation service for bidirectional translation."""

from models.slang import SlangTranslationResponse
from models.config import LLMConfig
from services.slang_lexicon_service import SlangLexiconService
from services.slang_matching_service import SlangMatchingService
from services.slang_llm_service import SlangLLMService
from utils.config import get_config_service
from utils.smart_logger import logger


class SlangService:
    """Unified service for all slang translation (GenZ ↔ English)."""

    def __init__(self):
        """Initialize slang translation services."""
        self.config_service = get_config_service()
        self.config = self.config_service.get_config(LLMConfig)

        # Initialize component services
        self._lexicon_service = SlangLexiconService(self.config)
        self._matching_service = SlangMatchingService(self.config)
        self._llm_service = SlangLLMService(self.config)

    def translate_to_english(self, text: str) -> SlangTranslationResponse:
        """
        Translate GenZ slang to plain English using hybrid approach.

        Uses lexicon-based matching + LLM for high-quality translations.

        Args:
            text: Input text containing GenZ slang

        Returns:
            SlangTranslationResponse with translation, confidence, and applied terms
        """
        try:
            # Load lexicon
            lexicon = self._lexicon_service.load_lexicon()
            if not lexicon:
                raise ValueError("Failed to load slang lexicon")

            # Extract slang terms using pattern matching
            automaton = self._matching_service.build_automaton(lexicon.items)
            spans = self._matching_service.match_lexicon(text.lower(), automaton)

            # LLM translation with context
            result = self._llm_service.translate_with_context(text, spans)

            return result

        except Exception as e:
            logger.log_error(e, {"operation": "slang_to_english", "text": text[:100]})
            # Re-raise for TranslationService to handle
            raise

    def translate_to_genz(self, text: str) -> SlangTranslationResponse:
        """
        Translate plain English to GenZ slang.

        Uses LLM to generate natural, current GenZ slang.

        Args:
            text: Input text in plain English

        Returns:
            SlangTranslationResponse with translation, confidence, and applied terms
        """
        try:
            # Use LLM for English → GenZ translation
            result = self._llm_service.translate_to_genz(text)

            return result

        except Exception as e:
            logger.log_error(e, {"operation": "english_to_genz", "text": text[:100]})
            # Re-raise for TranslationService to handle
            raise
