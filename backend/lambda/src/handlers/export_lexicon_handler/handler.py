"""Lambda handler for export lexicon (standalone utility function)."""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from aws_lambda_powertools.utilities.typing import LambdaContext

from repositories.slang_term_repository import SlangTermRepository
from utils.aws_services import aws_services
from utils.tracing import tracer
from utils.smart_logger import logger
from models.events import LexiconExportEvent


def convert_decimals_to_floats(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    else:
        return obj


def format_term_for_lexicon(dynamo_item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB item to lexicon JSON format."""
    # Convert Decimal to float for JSON serialization
    confidence = dynamo_item.get("lexicon_confidence", 0.85)
    if isinstance(confidence, Decimal):
        confidence = float(confidence)

    momentum = dynamo_item.get("lexicon_momentum", 1.0)
    if isinstance(momentum, Decimal):
        momentum = float(momentum)

    result = {
        "term": dynamo_item["slang_term"],
        "variants": dynamo_item.get("lexicon_variants", [dynamo_item["slang_term"]]),
        "pos": dynamo_item.get("lexicon_pos", "phrase"),
        "gloss": dynamo_item["meaning"],
        "examples": (
            [dynamo_item["example_usage"]] if dynamo_item.get("example_usage") else []
        ),
        "tags": dynamo_item.get("lexicon_tags", []),
        "status": "approved",
        "confidence": confidence,
        "regions": [],
        "age_rating": dynamo_item.get("lexicon_age_rating", "E"),
        "content_flags": dynamo_item.get("lexicon_content_flags", []),
        "first_seen": dynamo_item["created_at"][:10],
        "last_seen": dynamo_item.get("last_used_at", datetime.now().isoformat())[:10],
        "sources": {
            "reddit": 0,
            "youtube": 0,
            "runtime": dynamo_item.get("times_translated", 0),
        },
        "momentum": momentum,
        "categories": dynamo_item.get("lexicon_categories", ["slang"]),
    }

    # Ensure all Decimal values are converted
    return convert_decimals_to_floats(result)


# Initialize repository at module level (Lambda container reuse)
repository = SlangTermRepository()


# Lambda handler entry point - standalone utility function or SNS-triggered
@tracer.trace_lambda
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Export approved terms to S3 in lexicon format.

    Handles both:
    - SNS events (from approval notifications) - extracts message from SNS Records
    - Manual invocation (empty event or test events) - runs export directly
    """

    # Check if this is an SNS event (has Records array)
    sns_event: Optional[LexiconExportEvent] = None
    if event.get("Records"):
        try:
            # Extract SNS message from first record
            sns_record = event["Records"][0]
            if "Sns" in sns_record and "Message" in sns_record["Sns"]:
                message_str = sns_record["Sns"]["Message"]
                message_data = json.loads(message_str)

                # Only process approval notifications
                notification_type = message_data.get("notification_type")
                if notification_type in ["auto_approval", "manual_approval"]:
                    sns_event = LexiconExportEvent(
                        submission_id=message_data.get("submission_id"),
                        slang_term=message_data.get("slang_term"),
                        notification_type=notification_type,
                        approved_at=message_data.get("approved_at"),
                    )
                    logger.log_debug(
                        "Processing SNS approval event",
                        {
                            "notification_type": notification_type,
                            "submission_id": sns_event.submission_id,
                            "slang_term": sns_event.slang_term,
                        },
                    )
                else:
                    logger.log_debug(
                        "Skipping non-approval notification",
                        {"notification_type": notification_type},
                    )
                    return {
                        "statusCode": 200,
                        "body": json.dumps(
                            {"message": "Skipped: not an approval notification"}
                        ),
                    }
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.log_error(
                e,
                {"operation": "parse_sns_event", "event_structure": str(event.keys())},
            )
            # Fall through to manual export on parse error

    logger.log_debug(
        "Lexicon export request started",
        {
            "event_type": "lexicon_export_request",
            "trigger": "sns" if sns_event else "manual",
            "submission_id": sns_event.submission_id if sns_event else None,
        },
    )

    try:
        # Get all approved terms
        all_terms = repository.get_all_approved_terms()
        logger.log_debug(
            "Found approved terms",
            {
                "term_count": len(all_terms),
                "event_type": "terms_retrieved",
            },
        )

        # Format as lexicon JSON
        lexicon_items = []
        for term in all_terms:
            try:
                lexicon_items.append(format_term_for_lexicon(term))
            except Exception as e:
                logger.log_error(
                    e,
                    {
                        "operation": "format_term",
                        "term": term.get("slang_term", "unknown"),
                    },
                )
                continue

        lexicon_data = {
            "version": "3.0-dynamic",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(lexicon_items),
            "items": lexicon_items,
        }

        # Ensure all Decimal values are converted before JSON serialization
        lexicon_data = convert_decimals_to_floats(lexicon_data)

        # Upload to S3 using environment variables (same as lexicon service expects)
        bucket_name = os.environ["LEXICON_S3_BUCKET"]
        key_name = os.environ["LEXICON_S3_KEY"]

        s3_client = aws_services.s3_client
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=json.dumps(lexicon_data, indent=2),
            ContentType="application/json",
            CacheControl="public, max-age=3600",  # Cache for 1 hour
        )

        # Debug logging for successful response
        logger.log_debug(
            "Lexicon export completed successfully",
            {
                "terms_exported": len(lexicon_items),
                "bucket": bucket_name,
                "version": "3.0-dynamic",
                "event_type": "lexicon_export_success",
            },
        )

        # Business event logging
        logger.log_business_event(
            "lexicon_exported",
            {
                "term_count": len(lexicon_items),
                "version": "3.0-dynamic",
                "bucket": bucket_name,
            },
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Lexicon exported successfully",
                    "terms_exported": len(lexicon_items),
                    "bucket": bucket_name,
                    "version": "3.0-dynamic",
                }
            ),
        }

    except Exception as e:
        logger.log_error(e, {"operation": "export_lexicon"})
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Export failed", "error": str(e)}),
        }
