"""Initialize lexicon table by importing terms from default_lexicon.json."""

import json
import os
import sys
from typing import Any, Dict

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repositories.lexicon_repository import LexiconRepository  # noqa: E402
from models.quiz import QuizDifficulty, QuizCategory  # noqa: E402
from models.slang import (  # noqa: E402
    SlangTerm,
    ApprovalStatus,
    AgeRating,
    PartOfSpeech,
)
from utils.smart_logger import logger  # noqa: E402
from utils.tracing import tracer  # noqa: E402


def estimate_difficulty(item: Dict[str, Any]) -> QuizDifficulty:
    """Estimate difficulty based on confidence and momentum."""
    raw_confidence = item.get("confidence", 0.85)
    raw_momentum = item.get("momentum", 1.0)

    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.85

    try:
        momentum = float(raw_momentum)
    except (TypeError, ValueError):
        momentum = 1.0

    combined_score = confidence * momentum

    if combined_score >= 0.85:
        return QuizDifficulty.BEGINNER
    if combined_score >= 0.65:
        return QuizDifficulty.INTERMEDIATE
    return QuizDifficulty.ADVANCED


def map_categories(lexicon_categories: list) -> str:
    """Map lexicon categories to quiz categories."""
    category_map = {
        "acronym": QuizCategory.GENERAL,
        "approval": QuizCategory.APPROVAL,
        "disapproval": QuizCategory.DISAPPROVAL,
        "emotion": QuizCategory.EMOTION,
        "food": QuizCategory.FOOD,
        "appearance": QuizCategory.APPEARANCE,
        "social": QuizCategory.SOCIAL,
        "authenticity": QuizCategory.AUTHENTICITY,
        "intensity": QuizCategory.INTENSITY,
    }

    for cat in lexicon_categories:
        if cat in category_map:
            return category_map[cat]

    return QuizCategory.GENERAL


def parse_attestation_date(item: Dict[str, Any]) -> str:
    """Parse first_attested date with fallback to first_seen.

    Returns YYYY-MM-DD formatted date string.
    """
    # Try first_attested first
    first_attested = item.get("first_attested")
    if first_attested:
        # Validate format is YYYY-MM-DD
        try:
            # Simple validation - check it's YYYY-MM-DD format
            parts = first_attested.split("-")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                return first_attested
        except (AttributeError, ValueError):
            pass

    # Fallback to first_seen
    first_seen = item.get("first_seen", "2000-01-01")
    try:
        parts = first_seen.split("-")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return first_seen
    except (AttributeError, ValueError):
        pass

    # Default fallback
    return "2000-01-01"


# Removed build_gsi2_sort_key - no longer needed with new table structure


@tracer.trace_method("init_lexicon")
def init_lexicon():
    """Import all terms from default_lexicon.json into LexiconTable."""
    try:
        # Load lexicon data
        lexicon_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "lexicons", "default_lexicon.json"
        )

        with open(lexicon_path, "r", encoding="utf-8") as f:
            lexicon = json.load(f)

        logger.log_business_event(
            "lexicon_initialization_started",
            {
                "total_terms": lexicon.get("count", 0),
                "version": lexicon.get("version", "unknown"),
            },
        )

        repository = LexiconRepository()
        imported = 0
        failed = 0

        for item in lexicon.get("items", []):
            try:
                # Estimate difficulty and category
                difficulty = estimate_difficulty(item)
                category = map_categories(item.get("categories", []))

                # Note: Wrong options now generated from category pools at runtime
                # No need to generate/store per-term wrong options

                # Parse attestation date (prioritizes first_attested, falls back to first_seen)
                attestation_date = parse_attestation_date(item)
                confidence = item.get("confidence", 0.85)

                # Map age rating
                age_rating_str = item.get("age_rating", "E")
                try:
                    age_rating = AgeRating(age_rating_str)
                except ValueError:
                    age_rating = AgeRating.EVERYONE

                # Map part of speech
                pos_str = item.get("pos", "phrase")
                try:
                    pos = PartOfSpeech(pos_str)
                except ValueError:
                    pos = PartOfSpeech.PHRASE

                # Ensure gloss is a string (handle edge cases where it might be boolean)
                # JSON can have boolean true/false which Python parses as bool
                gloss_value = item.get("gloss", "")
                if isinstance(gloss_value, bool):
                    # Convert boolean True/False to string "true"/"false"
                    gloss_value = "true" if gloss_value else "false"
                elif not isinstance(gloss_value, str):
                    # Convert any other non-string to string
                    gloss_value = str(gloss_value)
                # Ensure it's not empty
                if not gloss_value:
                    gloss_value = item.get("term", "unknown")  # Fallback to term name

                # Build term data as dict first, ensuring all values are correct types
                term_data = {
                    "term": item["term"],
                    "variants": item.get("variants", [item["term"]]),
                    "pos": pos,
                    "gloss": str(gloss_value),  # Explicitly convert to string
                    "examples": item.get("examples", []),
                    "tags": item.get("tags", []),
                    "status": ApprovalStatus.APPROVED,
                    "confidence": float(confidence),
                    "regions": item.get("regions", []),
                    "age_rating": age_rating,
                    "content_flags": item.get("content_flags", []),
                    "first_seen": item.get("first_seen"),
                    "last_seen": item.get("last_seen"),
                    "sources": item.get("sources", {}),
                    "momentum": float(item.get("momentum", 1.0)),
                    "categories": item.get("categories", []),
                    # Quiz fields
                    "is_quiz_eligible": True,
                    "quiz_difficulty": difficulty,
                    "quiz_category": category,
                    "first_attested": attestation_date,
                    "first_attested_confidence": item.get("first_attested_confidence"),
                    "attestation_note": item.get("attestation_note"),
                    "times_in_quiz": 0,
                    "quiz_accuracy_rate": 0.5,  # Start with neutral accuracy
                }

                # Remove None values to avoid validation issues
                term_data = {k: v for k, v in term_data.items() if v is not None}

                # Create SlangTerm using model_validate to ensure proper type handling
                term = SlangTerm.model_validate(term_data)

                # Create the term using repository
                if repository.save_lexicon_term(term):
                    imported += 1
                else:
                    failed += 1
                    logger.log_error(
                        Exception(f"Failed to create lexicon term: {item['term']}"),
                        {"term": item["term"], "operation": "save_lexicon_term"},
                    )

                # Log progress every 50 terms
                if imported % 50 == 0:
                    logger.log_business_event(
                        "lexicon_initialization_progress",
                        {
                            "imported": imported,
                            "failed": failed,
                            "current_term": item["term"],
                        },
                    )

            except Exception as e:
                failed += 1
                logger.log_error(
                    e,
                    {
                        "term": item.get("term", "unknown"),
                        "operation": "init_lexicon_item",
                    },
                )

        logger.log_business_event(
            "lexicon_initialization_completed",
            {
                "total_imported": imported,
                "total_failed": failed,
                "success_rate": (
                    round((imported / (imported + failed)) * 100, 2)
                    if (imported + failed) > 0
                    else 0
                ),
            },
        )

        return imported, failed

    except Exception as e:
        logger.log_error(e, {"operation": "init_lexicon"})
        raise


if __name__ == "__main__":
    """Run the initialization when executed directly."""
    print("Starting lexicon initialization...")

    try:
        imported, failed = init_lexicon()
        print("Initialization completed successfully!")
        print(f"Imported: {imported} terms")
        print(f"Failed: {failed} terms")

        if failed > 0:
            print(f"Warning: {failed} terms failed to import. Check logs for details.")
            sys.exit(1)
        else:
            print("All terms imported successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)
