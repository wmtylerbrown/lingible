"""
Slang lexicon service for loading and managing slang dictionaries.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from models.slang import SlangLexicon, SlangTerm
from models.config import LLMConfig
from utils.smart_logger import logger
from utils.aws_services import aws_services


class SlangLexiconService:
    """Service for loading and managing slang lexicons."""

    def __init__(self, config: LLMConfig):
        """Initialize the lexicon service with configuration."""
        self.config = config
        self._lexicon: Optional[SlangLexicon] = None

    def load_lexicon(self) -> SlangLexicon:
        """Load the slang lexicon from S3 or local file."""
        if self._lexicon is not None:
            return self._lexicon

        try:
            if self.config.lexicon_local_path and os.path.exists(
                self.config.lexicon_local_path
            ):
                logger.log_business_event(
                    "lexicon_loading",
                    {"source": "local", "path": self.config.lexicon_local_path},
                )
                with open(self.config.lexicon_local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                logger.log_business_event(
                    "lexicon_loading",
                    {
                        "source": "s3",
                        "bucket": self.config.lexicon_s3_bucket,
                        "key": self.config.lexicon_s3_key,
                    },
                )
                response = aws_services.s3_client.get_object(
                    Bucket=self.config.lexicon_s3_bucket, Key=self.config.lexicon_s3_key
                )
                data = json.loads(response["Body"].read().decode("utf-8"))

            self._lexicon = SlangLexicon(**data)
            logger.log_business_event(
                "lexicon_loaded", {"term_count": self._lexicon.count}
            )
            return self._lexicon

        except Exception as e:
            logger.log_error(e, {"operation": "lexicon_loading"})
            raise RuntimeError(f"Failed to load slang lexicon: {e}")

    def get_lexicon(self) -> SlangLexicon:
        """Get the loaded lexicon, loading it if necessary."""
        return self.load_lexicon()

    def get_terms_by_confidence(self, min_confidence: float = 0.0) -> List[SlangTerm]:
        """Get terms filtered by minimum confidence."""
        lexicon = self.get_lexicon()
        return [term for term in lexicon.items if term.confidence >= min_confidence]

    def get_terms_by_age_rating(self, max_rating: str) -> List[SlangTerm]:
        """Get terms filtered by maximum age rating."""
        rating_order = {"E": 0, "T13": 1, "T16": 2, "M18": 3}
        max_rating_value = rating_order.get(max_rating, 3)

        lexicon = self.get_lexicon()
        return [
            term
            for term in lexicon.items
            if rating_order.get(term.age_rating, 3) <= max_rating_value
        ]

    def get_terms_by_category(self, category: str) -> List[SlangTerm]:
        """Get terms filtered by category."""
        lexicon = self.get_lexicon()
        return [term for term in lexicon.items if category in term.categories]

    def search_terms(self, query: str, exact_match: bool = False) -> List[SlangTerm]:
        """Search for terms matching a query."""
        lexicon = self.get_lexicon()
        query_lower = query.lower()

        results = []
        for term in lexicon.items:
            if exact_match:
                if query_lower == term.term.lower() or query_lower in [
                    v.lower() for v in term.variants
                ]:
                    results.append(term)
            else:
                if (
                    query_lower in term.term.lower()
                    or any(query_lower in v.lower() for v in term.variants)
                    or query_lower in term.gloss.lower()
                ):
                    results.append(term)

        return results

    def get_term_by_canonical(self, canonical: str) -> Optional[SlangTerm]:
        """Get a specific term by its canonical form."""
        lexicon = self.get_lexicon()
        for term in lexicon.items:
            if term.term.lower() == canonical.lower():
                return term
        return None

    def get_variant_mapping(self) -> Dict[str, List[Tuple[SlangTerm, str, float]]]:
        """Get a mapping of normalized variants to terms."""
        lexicon = self.get_lexicon()
        variant_map: Dict[str, List[Tuple[SlangTerm, str, float]]] = {}

        for term in lexicon.items:
            for variant in term.variants:
                normalized = self._normalize_variant(variant)
                if normalized not in variant_map:
                    variant_map[normalized] = []
                variant_map[normalized].append((term, variant, term.confidence))

        return variant_map

    def _normalize_variant(self, variant: str) -> str:
        """Normalize a variant for matching."""
        # Basic normalization - could be enhanced with leet speak, emoji handling, etc.
        return variant.lower().strip()
