"""LLM service for slang translation using AWS Bedrock."""

import json
from typing import List
from decimal import Decimal
from models.slang import TranslationSpan, SlangTranslationResponse
from models.config import LLMConfig
from utils.aws_services import aws_services
from utils.smart_logger import logger


class SlangLLMService:
    """Service for LLM-based slang translation with context."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._bedrock_client = aws_services.bedrock_client

    def translate_with_context(
        self, text: str, slang_spans: List[TranslationSpan]
    ) -> SlangTranslationResponse:
        """Translate GenZ slang to English using LLM with slang context."""
        # Always send to LLM, even if no spans found
        # LLM can identify slang that lexicon might have missed

        # Create prompt directly from spans
        prompt = self._create_genz_to_english_prompt(text, slang_spans)

        try:
            # Call Bedrock
            response = self._call_bedrock(prompt)
            return self._parse_llm_response(response)

        except Exception as e:
            logger.log_error(e, {"operation": "llm_translation", "text": text[:100]})
            # Fallback to simple replacement
            return SlangTranslationResponse(
                translated=self._fallback_translation(text, slang_spans),
                confidence=Decimal("0.3"),  # Low confidence for fallback
                applied_terms=[],
            )

    def translate_to_genz(self, text: str) -> SlangTranslationResponse:
        """Translate plain English to GenZ slang using LLM."""
        prompt = self._create_english_to_genz_prompt(text)

        try:
            # Call Bedrock
            response = self._call_bedrock(prompt)
            return self._parse_llm_response(response)

        except Exception as e:
            logger.log_error(
                e, {"operation": "english_to_genz_llm", "text": text[:100]}
            )
            # Fallback: return original text with low confidence
            return SlangTranslationResponse(
                translated=text, confidence=Decimal("0.1"), applied_terms=[]
            )

    def _create_genz_to_english_prompt(
        self, text: str, spans: List[TranslationSpan]
    ) -> str:
        """Create enhanced prompt with structured JSON output and confidence scoring."""

        # Build term→gloss mappings directly from spans
        term_mappings = {}
        if spans:
            for span in spans:
                if span.gloss:
                    term_mappings[span.canonical] = [span.gloss]

        # Build the prompt with or without term mappings
        term_mappings_text = ""
        if term_mappings:
            term_mappings_text = f"""- The following term→gloss mappings are available:\n{json.dumps(term_mappings, ensure_ascii=False)}
- Most are direct translations you can use (like "fire" → "excellent").
- Some are definitions rather than translations - use good judgment.
- For interjections/memes like "6 7", the gloss is explanatory; don't literally output it.
- Translate naturally based on what fits the context.\n"""
        else:
            term_mappings_text = (
                "- Identify and translate any slang terms you recognize.\n"
            )

        return f"""You are a precise, concise Gen Z slang translator. You excel at translating Gen Z slang to everyday English. Output ONLY valid JSON.

Rules:
{term_mappings_text}- Rate your confidence from 0.0 (very uncertain) to 1.0 (completely certain).
- If you have high confidence (≥0.8), make the translation even if it changes the text significantly.
- Return EXACTLY this JSON format: {{"clean_text":"translated text here","applied_terms":["term1","term2"],"confidence":0.95}}
- applied_terms must be an array of strings (slang terms that were translated)

Examples:
- "no cap" → "for real"
- "that's fire" → "that's amazing"
- "bet" → "okay"
- "periodt" → "exactly"
- "this slaps" → "this is excellent"

Confidence Guidelines:
- 0.9-1.0: Clear, obvious slang with direct translations
- 0.7-0.9: Good slang matches with minor ambiguity
- 0.5-0.7: Uncertain slang or context-dependent meaning
- 0.3-0.5: Very unclear or potentially not slang
- 0.0-0.3: No clear slang detected or very ambiguous

Text: "{text}"

Translate:"""

    def _call_bedrock(self, prompt: str) -> str:
        """Call AWS Bedrock for translation using Messages API."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }

        response = self._bedrock_client.invoke_model(
            modelId=self.config.model, body=json.dumps(body)
        )

        data = json.loads(response["body"].read())
        return data["content"][0]["text"]

    def _parse_llm_response(self, response: str) -> SlangTranslationResponse:
        """Parse structured JSON response from LLM."""
        # Log the raw response for debugging
        logger.log_debug("LLM Raw Response", {"response": response[:500]})

        try:
            # Clean the response - remove any markdown formatting or extra text
            cleaned_response = response.strip()

            # Try to extract JSON from the response if it's wrapped in markdown
            if "```json" in cleaned_response:
                start = cleaned_response.find("```json") + 7
                end = cleaned_response.find("```", start)
                if end != -1:
                    cleaned_response = cleaned_response[start:end].strip()
            elif "```" in cleaned_response:
                start = cleaned_response.find("```") + 3
                end = cleaned_response.find("```", start)
                if end != -1:
                    cleaned_response = cleaned_response[start:end].strip()

            # Try to parse as JSON
            data = json.loads(cleaned_response)

            # Extract fields with fallbacks
            translated = data.get(
                "clean_text", data.get("translated", data.get("text", ""))
            )
            applied_terms = data.get("applied_terms", data.get("terms", []))
            confidence = data.get("confidence", 0.5)

            # Validate confidence range
            if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
                confidence = 0.5  # Default to medium confidence

            # Validate and clean applied_terms
            if not isinstance(applied_terms, list):
                applied_terms = []
            else:
                # Clean applied_terms - ensure all items are strings
                cleaned_terms = []
                for term in applied_terms:
                    if isinstance(term, str):
                        cleaned_terms.append(term)
                    elif isinstance(term, dict):
                        # If it's a dict like {"hard launch": "reveal"}, extract the key
                        cleaned_terms.extend(list(term.keys()))
                    else:
                        # Convert other types to strings
                        cleaned_terms.append(str(term))
                applied_terms = cleaned_terms

            logger.log_debug(
                "LLM Parsed Response",
                {
                    "translated": translated[:100],
                    "applied_terms": applied_terms,
                    "confidence": confidence,
                },
            )

            return SlangTranslationResponse(
                translated=translated,
                applied_terms=applied_terms,
                confidence=Decimal(str(confidence)),
            )
        except json.JSONDecodeError as e:
            logger.log_debug(
                "LLM JSON Parse Error", {"error": str(e), "response": response[:200]}
            )
            # Fallback to simple text extraction
            return SlangTranslationResponse(
                translated=response.strip(),
                applied_terms=[],
                confidence=Decimal("0.3"),  # Low confidence for fallback
            )
        except Exception as e:
            logger.log_error(
                e, {"operation": "parse_llm_response", "response": response[:200]}
            )
            # Fallback to simple text extraction
            return SlangTranslationResponse(
                translated=response.strip(),
                applied_terms=[],
                confidence=Decimal("0.1"),  # Very low confidence for error fallback
            )

    def _fallback_translation(self, text: str, spans: List[TranslationSpan]) -> str:
        """Simple fallback translation without LLM."""
        result = text

        # Handle case where no spans are found
        if not spans:
            return result

        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            if span.gloss:
                result = result[: span.start] + span.gloss + result[span.end :]
        return result

    def _create_english_to_genz_prompt(self, text: str) -> str:
        """Create prompt for English to GenZ translation."""
        return f"""You are a precise GenZ translator. Output ONLY valid JSON.

Text: "{text}"

Rules:
- Use authentic GenZ slang that people actually say
- Keep the same meaning and energy level
- Make it sound natural and current
- Don't over-explain or be too formal
- Rate your confidence from 0.0 (very uncertain) to 1.0 (completely certain)
- If you have high confidence (≥0.8), make bold slang choices
- applied_terms must be an array of strings (slang terms that were added)
- Return EXACTLY this JSON format: {{"clean_text":"translated text here","applied_terms":["term1","term2"],"confidence":0.95}}

Examples:
- "that's really good" → "that's fire"
- "that person has an exceptionally confident and self-assured presence" → "it's giving main character energy"
- "for real" → "no cap"
- "okay" → "bet"
- "exactly" → "periodt"

Confidence Guidelines:
- 0.9-1.0: Perfect slang match, very natural
- 0.7-0.9: Good slang choice with minor alternatives
- 0.5-0.7: Uncertain, multiple slang options
- 0.3-0.5: Weak slang match or awkward phrasing
- 0.0-0.3: Very unclear or no good slang equivalent

Translate:"""
