"""Trending repository for trending terms data operations."""

from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal

from models.trending import TrendingTerm, TrendingCategory
from utils.logging import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class TrendingRepository:
    """Repository for trending terms data operations."""

    def __init__(self) -> None:
        """Initialize trending repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var('TRENDING_TABLE')
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "trending")
    def create_trending_term(self, term: TrendingTerm) -> bool:
        """Create a new trending term record."""
        try:
            item = {
                "PK": f"TRENDING#{term.term.upper()}",
                "SK": "TERM",
                "term": term.term,
                "definition": term.definition,
                "category": term.category,
                "popularity_score": Decimal(str(term.popularity_score)),
                "search_count": term.search_count,
                "translation_count": term.translation_count,
                "first_seen": term.first_seen.isoformat(),
                "last_updated": term.last_updated.isoformat(),
                "is_active": str(term.is_active),
                "example_usage": term.example_usage,
                "origin": term.origin,
                "related_terms": term.related_terms,
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (90 * 24 * 60 * 60)
                ),  # 90 days TTL for trending data
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            logger.log_error(
                e,
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
                    "PK": f"TRENDING#{term.upper()}",
                    "SK": "TERM",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return TrendingTerm(
                term=item["term"],
                definition=item["definition"],
                category=TrendingCategory(item["category"]),
                popularity_score=item["popularity_score"],
                search_count=item["search_count"],
                translation_count=item["translation_count"],
                first_seen=datetime.fromisoformat(item["first_seen"]),
                last_updated=datetime.fromisoformat(item["last_updated"]),
                is_active=item["is_active"] == "True",
                example_usage=item.get("example_usage"),
                origin=item.get("origin"),
                related_terms=item.get("related_terms", []),
            )

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
            item = {
                "PK": f"TRENDING#{term.term.upper()}",
                "SK": "TERM",
                "term": term.term,
                "definition": term.definition,
                "category": term.category,
                "popularity_score": Decimal(str(term.popularity_score)),
                "search_count": term.search_count,
                "translation_count": term.translation_count,
                "first_seen": term.first_seen.isoformat(),
                "last_updated": term.last_updated.isoformat(),
                "is_active": str(term.is_active),
                "example_usage": term.example_usage,
                "origin": term.origin,
                "related_terms": term.related_terms,
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
            # Use GSI for querying by category and popularity
            if category:
                index_name = "CategoryPopularityIndex"
                key_condition = "category = :category"
                expression_values: dict = {":category": category}
                # Add filter for active terms when using category index
                if active_only:
                    filter_expression = "is_active = :is_active"
                    expression_values[":is_active"] = str(active_only)
            else:
                index_name = "PopularityIndex"
                key_condition = "is_active = :is_active"
                expression_values = {":is_active": str(active_only)}
                filter_expression = None

            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition,
                "ExpressionAttributeValues": expression_values,
                "ScanIndexForward": False,  # Sort by popularity score descending
                "Limit": limit,
            }

            if filter_expression:
                query_params["FilterExpression"] = filter_expression

            response = self.table.query(**query_params)

            terms = []
            for item in response.get("Items", []):
                try:
                    term = TrendingTerm(
                        term=item["term"],
                        definition=item["definition"],
                        category=TrendingCategory(item["category"]),
                        popularity_score=item["popularity_score"],
                        search_count=item["search_count"],
                        translation_count=item["translation_count"],
                        first_seen=datetime.fromisoformat(item["first_seen"]),
                        last_updated=datetime.fromisoformat(item["last_updated"]),
                        is_active=item["is_active"] == "True",
                        example_usage=item.get("example_usage"),
                        origin=item.get("origin"),
                        related_terms=item.get("related_terms", []),
                    )
                    terms.append(term)
                except Exception as e:
                    logger.log_error(
                        e,
                        {
                            "operation": "parse_trending_term",
                            "item": item,
                        },
                    )
                    continue

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
            self.table.update_item(
                Key={
                    "PK": f"TRENDING#{term.upper()}",
                    "SK": "TERM",
                },
                UpdateExpression="SET search_count = if_not_exists(search_count, :zero) + :one, last_updated = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
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
            self.table.update_item(
                Key={
                    "PK": f"TRENDING#{term.upper()}",
                    "SK": "TERM",
                },
                UpdateExpression="SET translation_count = if_not_exists(translation_count, :zero) + :one, last_updated = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
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
                IndexName="PopularityIndex",
                KeyConditionExpression="is_active = :is_active",
                ExpressionAttributeValues={":is_active": "True"},
                Select="COUNT",
            )

            total_active = response.get("Count", 0)

            # Get count by category
            category_counts = {}
            for category in TrendingCategory:
                response = self.table.query(
                    IndexName="CategoryPopularityIndex",
                    KeyConditionExpression="category = :category",
                    FilterExpression="is_active = :is_active",
                    ExpressionAttributeValues={
                        ":category": category,
                        ":is_active": "True",
                    },
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
                    "PK": f"TRENDING#{term.upper()}",
                    "SK": "TERM",
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
