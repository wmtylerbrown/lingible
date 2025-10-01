"""
Slang matching service for Aho-Corasick pattern matching and template recognition.
"""

import re
import json
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import deque
from dataclasses import dataclass

from models.slang import (
    SlangTerm,
    TranslationSpan,
    AgeRating,
    AgeFilterMode,
    SourceType,
)
from models.config import LLMConfig
from utils.smart_logger import logger


@dataclass
class RuntimeTemplate:
    """Runtime template for pattern matching."""

    id: str
    pattern: re.Pattern
    render_func: Callable[[re.Match], str]
    confidence: float


class ACAutomaton:
    """Efficient multi-pattern string matching using Aho-Corasick algorithm."""

    def __init__(self):
        """Initialize the automaton."""
        self.next: List[Dict[str, int]] = []
        self.fail: List[int] = []
        self.out: List[List[Tuple[str, Dict[str, Any]]]] = []
        self._new()

    def _new(self) -> int:
        """Create a new state and return its index."""
        self.next.append({})
        self.fail.append(0)
        self.out.append([])
        return len(self.next) - 1

    def add_word(self, word: str, payload: Dict[str, Any]) -> None:
        """Add a word pattern with its payload."""
        node = 0
        for char in word:
            if char not in self.next[node]:
                self.next[node][char] = self._new()
            node = self.next[node][char]
        self.out[node].append((word, payload))

    def build(self) -> None:
        """Build the failure function for the automaton."""
        queue: deque[int] = deque()

        # Initialize failure function for depth 1
        for char, next_node in self.next[0].items():
            self.fail[next_node] = 0
            queue.append(next_node)

        # Build failure function for deeper levels
        while queue:
            current = queue.popleft()
            for char, next_node in self.next[current].items():
                queue.append(next_node)
                fail_state = self.fail[current]

                # Find the longest proper suffix that is also a prefix
                while char not in self.next[fail_state] and fail_state != 0:
                    fail_state = self.fail[fail_state]

                self.fail[next_node] = self.next[fail_state].get(char, 0)
                self.out[next_node].extend(self.out[self.fail[next_node]])

    def iter_matches(self, text: str):
        """Iterate over all matches in the text."""
        state = 0
        for i, char in enumerate(text):
            while char not in self.next[state] and state != 0:
                state = self.fail[state]
            state = self.next[state].get(char, 0)

            if self.out[state]:
                for pattern, payload in self.out[state]:
                    yield (i, pattern, payload)


class SlangMatchingService:
    """Service for matching slang terms and templates in text."""

    def __init__(self, config: LLMConfig):
        """Initialize the matching service."""
        self.config = config
        self._automaton: Optional[ACAutomaton] = None
        self._variant_index: Optional[Dict[str, List[Tuple[SlangTerm, str, float]]]] = (
            None
        )

        # Compile regex patterns for normalization
        self._repeat_run = re.compile(r"(.)\1{2,}")  # Collapse 3+ to 2
        self._camel_split1 = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
        self._camel_split2 = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")
        self._word_or_emoji = re.compile(
            r"[#@]?[A-Za-z0-9_'-]+|[\U0001F300-\U0001FAFF]"
        )

        # Leet speak mapping
        self._leet_map = str.maketrans(
            {
                "0": "o",
                "1": "i",
                "3": "e",
                "4": "a",
                "5": "s",
                "7": "t",
                "8": "b",
                "$": "s",
                "@": "a",
                "!": "i",
            }
        )

        # Emoji aliases
        self._emoji_aliases = {
            "💀": "skull emoji",
            "😂": "skull emoji",
            "🤣": "skull emoji",
            "😭": "skull emoji",
        }

        # Template patterns for complex slang expressions
        self._templates: List[RuntimeTemplate] = [
            RuntimeTemplate(
                id="its_giving",
                pattern=re.compile(
                    r"\b(it'?s)\s+giving\s+(?P<X>[^.,!?;:\n\r]{1,40})", re.IGNORECASE
                ),
                render_func=lambda m: f"it gives off a {m.group('X').strip()} vibe",
                confidence=0.85,
            ),
            RuntimeTemplate(
                id="adj_af",
                pattern=re.compile(r"\b(?P<ADJ>[a-zA-Z]+)\s+af\b", re.IGNORECASE),
                render_func=lambda m: f"very {m.group('ADJ')}",
                confidence=0.85,
            ),
            RuntimeTemplate(
                id="left_no_crumbs",
                pattern=re.compile(
                    r"\b(?P<VERB>[a-zA-Z]+)\s+and\s+left\s+no\s+crumbs\b", re.IGNORECASE
                ),
                render_func=lambda m: f"did {m.group('VERB')} extremely well",
                confidence=0.9,
            ),
        ]

    def build_automaton(self, terms: List[SlangTerm]) -> ACAutomaton:
        """Build the Aho-Corasick automaton from slang terms."""
        if self._automaton is not None:
            return self._automaton

        automaton = ACAutomaton()
        rating_order = {
            AgeRating.EVERYONE: 0,
            AgeRating.TEEN_13: 1,
            AgeRating.TEEN_16: 2,
            AgeRating.MATURE_18: 3,
        }
        max_rating_value = rating_order.get(AgeRating(self.config.age_max_rating), 3)

        for term in terms:
            # Skip terms that exceed age rating
            if rating_order.get(term.age_rating, 3) > max_rating_value:
                if AgeFilterMode(self.config.age_filter_mode) == AgeFilterMode.ANNOTATE:
                    # Add placeholder for filtered terms
                    for variant in term.variants:
                        payload = {
                            "canonical": term.term,
                            "entry": term,
                            "variant": variant.lower(),
                            "single_word": " " not in variant,
                            "confidence": term.confidence,
                            "age_rating": term.age_rating,
                            "content_flags": term.content_flags,
                            "filtered": True,
                        }
                        automaton.add_word(variant.lower(), payload)
                continue

            for variant in term.variants:
                payload = {
                    "canonical": term.term,
                    "entry": term,
                    "variant": variant.lower(),
                    "single_word": " " not in variant,
                    "confidence": term.confidence,
                    "age_rating": term.age_rating,
                    "content_flags": term.content_flags,
                    "filtered": False,
                }
                automaton.add_word(variant.lower(), payload)

        automaton.build()
        self._automaton = automaton
        logger.log_business_event("automaton_built", {"term_count": len(terms)})
        return automaton

    def match_lexicon(self, text: str, automaton: ACAutomaton) -> List[TranslationSpan]:
        """Match slang terms in text using the automaton."""
        spans = []
        text_lower = text.lower()

        for end_idx, pattern, payload in automaton.iter_matches(text_lower):
            start = end_idx - len(pattern) + 1

            # Check word boundaries for single words
            if payload.get("single_word", False) and " " not in pattern:
                prev_char = text_lower[start - 1] if start > 0 else " "
                next_char = (
                    text_lower[end_idx + 1] if end_idx + 1 < len(text_lower) else " "
                )
                if self._is_word_char(prev_char) or self._is_word_char(next_char):
                    continue

            entry = payload["entry"]
            age = entry.age_rating
            gloss = None
            meta = {
                "needs_sense": "senses" in entry.__dict__,
                "age_rating": age,
                "content_flags": entry.content_flags,
                "filtered": payload.get("filtered", False),
            }

            if entry.senses:
                meta["senses"] = entry.senses
            else:
                gloss = entry.gloss

            if payload.get("filtered", False):
                gloss = "[filtered by age]"

            span = TranslationSpan(
                start=start,
                end=end_idx + 1,
                surface=text[start : end_idx + 1],
                source=SourceType.LEXEME,
                canonical=entry.term,
                gloss=gloss,
                confidence=entry.confidence,
                meta=meta,
            )
            spans.append(span)

        return spans

    def match_templates(self, text: str) -> List[TranslationSpan]:
        spans: List[TranslationSpan] = []
        tl = text.lower()

        # --- Helper maps/stoplist for better English & fewer false positives ---
        base_map = {
            "norm": "neutral",  # normcore -> neutral aesthetic
            "gorp": "outdoor gear",  # gorpcore -> outdoor-gear aesthetic
            "y2k": "y2k",
            "clean-girl": "minimal",  # optional taste choice
        }
        # words ending with "core" we do NOT want to treat as aesthetics
        core_stop = {"hardcore", "encore", "socore"}  # add any you hit

        # ========== Template 1: "it's giving" ==========
        for g in re.finditer(r"\bit['’]s giving\b", tl):
            a, b = g.start(), g.end()
            spans.append(
                TranslationSpan(
                    start=a,
                    end=b,
                    surface=text[a:b],
                    source=SourceType.TEMPLATE,
                    canonical="it's giving",
                    gloss="gives off a certain vibe",
                    confidence=0.80,
                    meta={},
                )
            )

        # ========== Template 2: X-core (hyphen optional) ==========
        # Examples: barbiecore, dark-academia-core, gorpcore
        for m in re.finditer(r"\b([a-z][a-z0-9']+)(?:-)?core\b", tl):
            whole = m.group(0)
            if whole in core_stop:
                continue
            base = m.group(1)
            nice = base_map.get(base, base)
            # Two short gloss options; render_clean may randomize between them
            gloss = f"{nice} aesthetic;{nice} style"
            a, b = m.start(), m.end()
            spans.append(
                TranslationSpan(
                    start=a,
                    end=b,
                    surface=text[a:b],
                    source=SourceType.TEMPLATE,
                    canonical="-core",
                    gloss=gloss,
                    confidence=0.80,
                    meta={"base": base},
                )
            )

        # ========== Template 3: X aesthetic ==========
        # Examples: dark academia aesthetic, y2k aesthetic, coquette aesthetic
        # Keep it conservative to avoid false positives; capture the base phrase.
        for m in re.finditer(r"\b([a-z0-9][a-z0-9' ]+?)\s+aesthetic\b", tl):
            base = re.sub(r"\s+", " ", m.group(1).strip())
            # normalize a couple of bases (optional taste)
            base_key = base.replace(" ", "-")
            nice = base_map.get(base_key, base_key)
            gloss = f"{nice} aesthetic;{nice} style"
            a, b = m.start(), m.end()
            spans.append(
                TranslationSpan(
                    start=a,
                    end=b,
                    surface=text[a:b],
                    source=SourceType.TEMPLATE,
                    canonical="X aesthetic",
                    gloss=gloss,
                    confidence=0.78,
                    meta={"base": base},
                )
            )

        # ========== Template 4: X-pilled ==========
        for m3 in re.finditer(r"\b([a-z]+)-pilled\b", tl):
            a, b = m3.start(), m3.end()
            spans.append(
                TranslationSpan(
                    start=a,
                    end=b,
                    surface=text[a:b],
                    source=SourceType.TEMPLATE,
                    canonical="-pilled",
                    gloss="obsessed;indoctrinated",
                    confidence=0.78,
                    meta={"base": m3.group(1)},
                )
            )

        return spans

    def resolve_overlaps(self, spans: List[TranslationSpan]) -> List[TranslationSpan]:
        """Resolve overlapping spans by preferring higher confidence and templates."""
        if not spans:
            return spans

        # Sort by start position, then by length (desc), then by confidence (desc), then by source
        def sort_key(span: TranslationSpan) -> Tuple[int, int, float, int]:
            source_priority = 0 if span.source == "template" else 1
            return (span.start, -span.length, -span.confidence, source_priority)

        sorted_spans = sorted(spans, key=sort_key)
        chosen = []
        last_end = -1

        for span in sorted_spans:
            if span.start >= last_end:
                chosen.append(span)
                last_end = span.end

        return chosen

    def match_variant_fallbacks(
        self,
        text: str,
        chosen_spans: List[TranslationSpan],
        variant_index: Dict[str, List[Tuple[SlangTerm, str, float]]],
    ) -> List[TranslationSpan]:
        """Create soft matches from normalized forms for uncovered tokens."""
        covered: set[int] = set()
        for span in chosen_spans:
            covered.update(range(span.start, span.end))

        fallback_spans = []
        rating_order = {
            AgeRating.EVERYONE: 0,
            AgeRating.TEEN_13: 1,
            AgeRating.TEEN_16: 2,
            AgeRating.MATURE_18: 3,
        }
        max_rating_value = rating_order.get(AgeRating(self.config.age_max_rating), 3)

        for match in self._word_or_emoji.finditer(text):
            start, end = match.start(), match.end()
            if any(i in covered for i in range(start, end)):
                continue

            token = match.group(0)
            meta = {}

            # Handle hashtags
            if token.startswith("#"):
                phrase = self._split_hashtag(token)
                normalized = self._normalize_token(phrase)
                meta["matched_via"] = "hashtag"
            else:
                normalized = self._normalize_token(token)
                meta["matched_via"] = "norm" if normalized != token else "norm_same"

            if normalized in variant_index:
                # Pick best by confidence
                term, variant, confidence = sorted(
                    variant_index[normalized], key=lambda x: -x[2]
                )[0]

                # Age gate
                age = term.age_rating
                if rating_order.get(age, 3) > max_rating_value:
                    if (
                        AgeFilterMode(self.config.age_filter_mode)
                        == AgeFilterMode.ANNOTATE
                    ):
                        fallback_spans.append(
                            TranslationSpan(
                                start=start,
                                end=end,
                                surface=token,
                                source=SourceType.LEXEME,
                                canonical=term.term,
                                gloss="[filtered by age]",
                                confidence=confidence * 0.95,
                                meta={"age_rating": age, "filtered": True, **meta},
                            )
                        )
                    continue

                # Prepare gloss/meta
                if term.senses:
                    gloss = None
                    meta.update(
                        {
                            "needs_sense": "true",
                            "senses": (
                                json.dumps(
                                    [sense.model_dump() for sense in term.senses]
                                )
                                if term.senses
                                else "[]"
                            ),
                            "age_rating": age,
                            "content_flags": json.dumps(term.content_flags),
                            "filtered": "false",
                        }
                    )
                else:
                    gloss = term.gloss
                    meta.update(
                        {
                            "age_rating": age,
                            "content_flags": json.dumps(term.content_flags),
                            "filtered": "false",
                        }
                    )

                fallback_spans.append(
                    TranslationSpan(
                        start=start,
                        end=end,
                        surface=token,
                        source=SourceType.LEXEME,
                        canonical=term.term,
                        gloss=gloss,
                        confidence=confidence * 0.95,
                        meta=meta,
                    )
                )

        return fallback_spans

    def _is_word_char(self, char: str) -> bool:
        """Check if character is a word character."""
        return char.isalnum() or char == "_"

    def _normalize_token(self, token: str) -> str:
        """Normalize a token for matching."""
        # Emoji alias first
        if token in self._emoji_aliases:
            return self._emoji_aliases[token]

        normalized = token.lower()
        normalized = normalized.translate(self._leet_map)
        normalized = self._repeat_run.sub(r"\1\1", normalized)
        return normalized

    def _split_hashtag(self, tag: str) -> str:
        """Split a hashtag into words."""
        text = tag.strip("#")
        text = self._camel_split2.sub(" ", self._camel_split1.sub(" ", text))
        text = text.replace("_", " ").replace("-", " ")
        return " ".join(text.split()).lower()
