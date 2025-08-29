"""Translation repository for DynamoDB operations."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..models.translations import (
    TranslationHistory,
    TranslationDirection,
)
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.aws_services import aws_services
from ..utils.config import get_config
from .base_repository import QueryResult


class TranslationRepository:
    """Repository for translation data operations."""

    def __init__(self) -> None:
        """Initialize translation repository."""
        self.config = get_config()
        self.table_name = self.config.get_database_config()["translations_table"]
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "translations")
    def create_translation(self, translation: TranslationHistory) -> bool:
        """Create a new translation record."""
        try:
            item = {
                "PK": f"USER#{translation.user_id}",
                "SK": f"TRANSLATION#{translation.translation_id}",
                "translation_id": translation.translation_id,
                "user_id": translation.user_id,
                "original_text": translation.original_text,
                "translated_text": translation.translated_text,
                "direction": translation.direction.value,
                "confidence_score": translation.confidence_score,
                "created_at": translation.created_at.isoformat(),
                "model_used": translation.model_used,
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            logger.log_business_event(
                "translation_created",
                {
                    "translation_id": translation.translation_id,
                    "user_id": translation.user_id,
                    "direction": translation.direction.value,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_translation",
                    "translation_id": translation.translation_id,
                    "user_id": translation.user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "translations")
    def get_translation(
        self, user_id: str, translation_id: str
    ) -> Optional[TranslationHistory]:
        """Get a specific translation by ID."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"TRANSLATION#{translation_id}",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return TranslationHistory(
                translation_id=item["translation_id"],
                user_id=item["user_id"],
                original_text=item["original_text"],
                translated_text=item["translated_text"],
                direction=TranslationDirection(item["direction"]),
                confidence_score=item.get("confidence_score"),
                created_at=datetime.fromisoformat(item["created_at"]),
                model_used=item.get("model_used"),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_translation",
                    "translation_id": translation_id,
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("query", "translations")
    def get_user_translations(
        self,
        user_id: str,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> QueryResult[TranslationHistory]:
        """Get translations for a specific user."""
        try:
            query_kwargs: Dict[str, Any] = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": f"USER#{user_id}"},
                "ScanIndexForward": False,  # Most recent first
                "Limit": limit,
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)

            translations = []
            for item in response.get("Items", []):
                if item["SK"].startswith("TRANSLATION#"):
                    translations.append(
                        TranslationHistory(
                            translation_id=item["translation_id"],
                            user_id=item["user_id"],
                            original_text=item["original_text"],
                            translated_text=item["translated_text"],
                            direction=TranslationDirection(item["direction"]),
                            confidence_score=item.get("confidence_score"),
                            created_at=datetime.fromisoformat(item["created_at"]),
                            model_used=item.get("model_used"),
                        )
                    )

            return QueryResult(
                items=translations,
                last_evaluated_key=response.get("LastEvaluatedKey"),
                count=len(translations),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user_translations",
                    "user_id": user_id,
                    "limit": limit,
                },
            )
            return QueryResult(items=[], last_evaluated_key=None, count=0)

    @tracer.trace_database_operation("delete", "translations")
    def delete_translation(self, user_id: str, translation_id: str) -> bool:
        """Delete a translation record."""
        try:
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"TRANSLATION#{translation_id}",
                }
            )

            logger.log_business_event(
                "translation_deleted",
                {
                    "translation_id": translation_id,
                    "user_id": user_id,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_translation",
                    "translation_id": translation_id,
                    "user_id": user_id,
                },
            )
            return False

    def generate_translation_id(self) -> str:
        """Generate a unique translation ID."""
        return str(uuid.uuid4())
