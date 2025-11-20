"""Trending repository for trending terms data operations."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal

from models.trending import TrendingTerm, TrendingCategory
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class TrendingRepository:
    """Repository for trending terms data operations."""

    def __init__(self) -> None:
        """Initialize trending repository."""
        config_service = get_config_service()
        self.table_name = config_service._get_env_var("TRENDING_TABLE")
        self.table = aws_services.get_table(self.table_name)

    def _item_to_trending_term(self, item: Dict[str, Any]) -> Optional[TrendingTerm]:
        try:
            is_active_raw = item.get("is_active_flag", item.get("is_active", True))
            if isinstance(is_active_raw, str):
                is_active = is_active_raw.lower().endswith("true")
            else:
                is_active = bool(is_active_raw)
            return TrendingTerm(
                term=item["term"],
                definition=item["definition"],
                category=item["category"],
                popularity_score=self._to_decimal(
                    item.get("popularity_score", Decimal("0"))
                ),
                search_count=int(item.get("search_count", 0)),
                translation_count=int(item.get("translation_count", 0)),
                first_seen=item["first_seen"],
                last_updated=item["last_updated"],
                is_active=is_active,
                example_usage=item.get("example_usage"),
                origin=item.get("origin"),
                related_terms=item.get("related_terms", []),
            )
        except KeyError as exc:
            logger.log_error(
                exc,
                {
                    "operation": "_item_to_trending_term",
                    "item": item,
                },
            )
            return None

    def _base_item(self, term: TrendingTerm) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        category_value = (
            term.category.value
            if isinstance(term.category, TrendingCategory)
            else str(term.category)
        )
        item = {
            "PK": f"TERM#{term.term.lower()}",
            "SK": "METADATA#trending",
            "term": term.term,
            "definition": term.definition,
            "category": category_value,
            "popularity_score": term.popularity_score,  # Already Decimal, no conversion needed
            "search_count": term.search_count,
            "translation_count": term.translation_count,
            "first_seen": term.first_seen.isoformat(),
            "last_updated": term.last_updated.isoformat(),
            "is_active": f"ACTIVE#{term.is_active}",
            "is_active_flag": term.is_active,
            "example_usage": term.example_usage,
            "origin": term.origin,
            "related_terms": term.related_terms,
            "ttl": int(now.timestamp() + (90 * 24 * 60 * 60)),
        }
        return {k: v for k, v in item.items() if v is not None}

    def _to_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @tracer.trace_database_operation("create", "trending")
    def create_trending_term(self, term: TrendingTerm) -> bool:
        """Create a new trending term record."""
        try:
            self.table.put_item(Item=self._base_item(term))
            return True
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "create_trending_term",
                    "term": term.term,
                },
            )
            return False

    @tracer.trace_database_operation("get", "trending")
    def get_trending_term(self, term: str) -> Optional[TrendingTerm]:
        """Get trending term by name."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"TERM#{term.lower()}",
                    "SK": "METADATA#trending",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            trending_term = self._item_to_trending_term(item)
            if trending_term is None:
                return None
            return trending_term

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_trending_term",
                    "term": term,
                },
            )
            return None

    @tracer.trace_database_operation("update", "trending")
    def update_trending_term(self, term: TrendingTerm) -> bool:
        """Update trending term record."""
        try:
            category_value = (
                term.category.value
                if isinstance(term.category, TrendingCategory)
                else str(term.category)
            )
            item = {
                "PK": f"TERM#{term.term.lower()}",
                "SK": "METADATA#trending",
                "term": term.term,
                "definition": term.definition,
                "category": category_value,
                "popularity_score": term.popularity_score,  # Already Decimal, no conversion needed
                "search_count": term.search_count,
                "translation_count": term.translation_count,
                "first_seen": term.first_seen.isoformat(),
                "last_updated": term.last_updated.isoformat(),
                "is_active": f"ACTIVE#{term.is_active}",
                "is_active_flag": term.is_active,
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_trending_term",
                    "term": term.term,
                },
            )
            return False

    @tracer.trace_database_operation("query", "trending")
    def get_trending_terms(
        self,
        limit: int = 50,
        category: Optional[TrendingCategory] = None,
        active_only: bool = True,
    ) -> List[TrendingTerm]:
        """Get list of trending terms with optional filtering."""
        try:
            if category:
                category_value = (
                    category.value
                    if isinstance(category, TrendingCategory)
                    else str(category)
                )
                expression_values: Dict[str, Any] = {":category": category_value}
                query_params: Dict[str, Any] = {
                    "IndexName": "TrendingCategoryIndex",
                    "KeyConditionExpression": "category = :category",
                    "ExpressionAttributeValues": expression_values,
                    "Limit": limit,
                    "ScanIndexForward": False,
                }
                if active_only:
                    expression_values[":is_active"] = "ACTIVE#True"
                    query_params["FilterExpression"] = "is_active = :is_active"
                response = self.table.query(**query_params)
            else:
                response = self.table.query(
                    IndexName="TrendingActiveIndex",
                    KeyConditionExpression="is_active = :is_active",
                    ExpressionAttributeValues={":is_active": f"ACTIVE#{active_only}"},
                    Limit=limit,
                    ScanIndexForward=False,
                )

            terms = []
            for item in response.get("Items", []):
                source_item = item
                if (
                    ("first_seen" not in item or "last_updated" not in item)
                    and "PK" in item
                    and "SK" in item
                ):
                    source_item = (
                        self.table.get_item(
                            Key={"PK": item["PK"], "SK": item["SK"]}
                        ).get("Item")
                        or item
                    )
                term = self._item_to_trending_term(source_item)
                if term is not None:
                    terms.append(term)

            return terms

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_trending_terms",
                    "limit": limit,
                    "category": category if category else None,
                },
            )
            return []

    @tracer.trace_database_operation("update", "trending")
    def increment_search_count(self, term: str) -> bool:
        """Increment search count for a trending term."""
        try:
            # First get the term to know its is_active and category for GSI updates
            existing_term = self.get_trending_term(term)
            if not existing_term:
                logger.log_debug(
                    f"Cannot increment search count for non-existent term: {term}"
                )
                return False

            # Update item with GSI fields
            self.table.update_item(
                Key={
                    "PK": f"TERM#{term.lower()}",
                    "SK": "METADATA#trending",
                },
                UpdateExpression=(
                    "SET search_count = if_not_exists(search_count, :zero) + :one, "
                    "last_updated = :updated_at, "
                    "is_active = :is_active, "
                    "category = :category"
                ),
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                    ":is_active": f"ACTIVE#{existing_term.is_active}",
                    ":category": (
                        existing_term.category.value
                        if isinstance(existing_term.category, TrendingCategory)
                        else str(existing_term.category)
                    ),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_search_count",
                    "term": term,
                },
            )
            return False

    @tracer.trace_database_operation("update", "trending")
    def increment_translation_count(self, term: str) -> bool:
        """Increment translation count for a trending term."""
        try:
            # First get the term to know its is_active and category for GSI updates
            existing_term = self.get_trending_term(term)
            if not existing_term:
                logger.log_debug(
                    f"Cannot increment translation count for non-existent term: {term}"
                )
                return False

            # Update item with GSI fields
            self.table.update_item(
                Key={
                    "PK": f"TERM#{term.lower()}",
                    "SK": "METADATA#trending",
                },
                UpdateExpression=(
                    "SET translation_count = if_not_exists(translation_count, :zero) + :one, "
                    "last_updated = :updated_at, "
                    "is_active = :is_active, "
                    "category = :category"
                ),
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                    ":is_active": f"ACTIVE#{existing_term.is_active}",
                    ":category": (
                        existing_term.category.value
                        if isinstance(existing_term.category, TrendingCategory)
                        else str(existing_term.category)
                    ),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_translation_count",
                    "term": term,
                },
            )
            return False

    @tracer.trace_database_operation("query", "trending")
    def get_trending_stats(self) -> dict:
        """Get trending statistics."""
        try:
            # Get total count of active trending terms
            response = self.table.query(
                IndexName="TrendingActiveIndex",
                KeyConditionExpression="is_active = :is_active",
                ExpressionAttributeValues={":is_active": "ACTIVE#True"},
                Select="COUNT",
            )

            total_active = response.get("Count", 0)

            # Get count by category
            category_counts = {}
            for category in TrendingCategory:
                response = self.table.query(
                    IndexName="TrendingCategoryIndex",
                    KeyConditionExpression="category = :category",
                    ExpressionAttributeValues={
                        ":category": category.value,
                        ":is_active": "ACTIVE#True",
                    },
                    FilterExpression="is_active = :is_active",
                    Select="COUNT",
                )
                category_counts[category] = response.get("Count", 0)

            return {
                "total_active_terms": total_active,
                "category_counts": category_counts,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "get_trending_stats"},
            )
            return {
                "total_active_terms": 0,
                "category_counts": {},
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    @tracer.trace_database_operation("delete", "trending")
    def delete_trending_term(self, term: str) -> bool:
        """Delete a trending term."""
        try:
            self.table.delete_item(
                Key={
                    "PK": f"TERM#{term.lower()}",
                    "SK": "METADATA#trending",
                }
            )

            logger.log_business_event(
                "trending_term_deleted",
                {
                    "term": term,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_trending_term",
                    "term": term,
                },
            )
            return False
