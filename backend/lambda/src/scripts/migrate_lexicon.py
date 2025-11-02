"""One-time script to import updated_lexicon.json into slang_terms table."""

import json
import os
import sys
from decimal import Decimal
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repositories.slang_term_repository import SlangTermRepository  # noqa: E402
from models.quiz import QuizDifficulty, QuizCategory  # noqa: E402
from utils.smart_logger import logger  # noqa: E402
from utils.tracing import tracer  # noqa: E402


def estimate_difficulty(item: Dict[str, Any]) -> str:
    """Estimate difficulty based on confidence and momentum."""
    confidence = item.get("confidence", 0.85)
    momentum = item.get("momentum", 1.0)

    # Combine confidence and momentum for difficulty assessment
    combined_score = confidence * momentum

    if combined_score >= 0.9:
        return QuizDifficulty.BEGINNER
    elif combined_score >= 0.7:
        return QuizDifficulty.INTERMEDIATE
    else:
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


def build_gsi2_sort_key(attestation_date: str, confidence: float, term: str) -> str:
    """Build GSI2SK sort key prioritizing newer terms.

    Format: {reverse_date:08d}#{confidence:04d}#{term}
    - reverse_date: YYYYMMDD as integer (newer dates = higher numbers for descending sort)
    - confidence: confidence score as 4-digit integer (0-100)
    - term: term name for lexicographic tie-breaking

    Example: "2021-11-01" with 85% confidence, term "mid" → "20211101#0085#mid"
    """
    # Convert YYYY-MM-DD to YYYYMMDD integer
    reverse_date = int(attestation_date.replace("-", ""))
    confidence_score = int(confidence * 100)
    return f"{reverse_date:08d}#{confidence_score:04d}#{term}"


@tracer.trace_method("migrate_lexicon")
def migrate_lexicon():
    """Import all terms from updated_lexicon.json."""
    try:
        # Load lexicon data
        lexicon_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "lexicons", "updated_lexicon.json"
        )

        with open(lexicon_path, "r", encoding="utf-8") as f:
            lexicon = json.load(f)

        logger.log_business_event(
            "lexicon_migration_started",
            {
                "total_terms": lexicon.get("count", 0),
                "version": lexicon.get("version", "unknown"),
            },
        )

        repository = SlangTermRepository()
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

                # Build GSI2SK with date-based prioritization
                gsi2sk = build_gsi2_sort_key(attestation_date, confidence, item["term"])

                # Create term data
                term_data = {
                    "PK": f"TERM#{item['term'].lower()}",
                    "SK": f"SOURCE#lexicon#{item['term'].lower()}",
                    "slang_term": item["term"],
                    "meaning": item["gloss"],
                    "example_usage": (
                        item["examples"][0] if item.get("examples") else None
                    ),
                    "context": "lexicon",
                    "original_translation_id": None,
                    # Source tracking
                    "source": "lexicon",
                    "source_id": item["term"],
                    # Status (lexicon terms are always approved)
                    "status": "approved",
                    "created_at": f"{item.get('first_seen', '2023-01-01')}T00:00:00Z",
                    "reviewed_at": f"{item.get('first_seen', '2023-01-01')}T00:00:00Z",
                    "reviewed_by": "system",
                    "approval_type": "lexicon",
                    # Lexicon metadata
                    "lexicon_variants": item.get("variants", [item["term"]]),
                    "lexicon_pos": item.get("pos", "phrase"),
                    "lexicon_tags": item.get("tags", []),
                    "lexicon_confidence": Decimal(str(confidence)),
                    "lexicon_age_rating": item.get("age_rating", "E"),
                    "lexicon_content_flags": item.get("content_flags", []),
                    "lexicon_categories": item.get("categories", []),
                    "lexicon_momentum": Decimal(str(item.get("momentum", 1.0))),
                    # Attestation fields (new)
                    "first_attested": attestation_date,
                    "first_attested_confidence": item.get("first_attested_confidence"),
                    "attestation_note": item.get("attestation_note"),
                    # Quiz fields
                    "is_quiz_eligible": True,
                    "quiz_difficulty": difficulty,
                    "quiz_category": category,
                    # Note: quiz_wrong_options removed - now using category-based pools
                    "times_in_quiz": 0,
                    "quiz_accuracy_rate": Decimal("0.5"),  # Start with neutral accuracy
                    # Usage statistics
                    "times_translated": 0,
                    "popularity_score": int(confidence * 100),
                    "last_used_at": f"{item.get('last_seen', '2023-01-01')}T00:00:00Z",
                    "exported_to_s3": False,
                    "last_exported_at": None,
                    # GSI fields for all access patterns
                    "GSI1PK": "STATUS#approved",
                    "GSI1SK": f"{item.get('first_seen', '2023-01-01')}T00:00:00Z",
                    "GSI2PK": f"QUIZ#{difficulty}",
                    "GSI2SK": gsi2sk,  # Date-prioritized sort key
                    "GSI3PK": f"CATEGORY#{category}",
                    "GSI3SK": item["term"],
                    "GSI4PK": "SOURCE#lexicon",
                    "GSI4SK": item["term"],
                }

                # Remove None values
                term_data = {k: v for k, v in term_data.items() if v is not None}

                # Create the term
                if repository.create_lexicon_term(term_data):
                    imported += 1
                else:
                    failed += 1
                    logger.log_error(
                        Exception(f"Failed to create lexicon term: {item['term']}"),
                        {"term": item["term"], "operation": "create_lexicon_term"},
                    )

                # Log progress every 50 terms
                if imported % 50 == 0:
                    logger.log_business_event(
                        "lexicon_migration_progress",
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
                        "operation": "migrate_lexicon_item",
                    },
                )

        logger.log_business_event(
            "lexicon_migration_completed",
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
        logger.log_error(e, {"operation": "migrate_lexicon"})
        raise


if __name__ == "__main__":
    """Run the migration when executed directly."""
    print("Starting lexicon migration...")

    try:
        imported, failed = migrate_lexicon()
        print("Migration completed successfully!")
        print(f"Imported: {imported} terms")
        print(f"Failed: {failed} terms")

        if failed > 0:
            print(f"Warning: {failed} terms failed to import. Check logs for details.")
            sys.exit(1)
        else:
            print("All terms imported successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
