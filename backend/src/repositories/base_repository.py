"""Base repository for DynamoDB operations."""

from typing import Generic, TypeVar, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from botocore.exceptions import ClientError
from dataclasses import dataclass

from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.aws_services import aws_services


T = TypeVar("T")


@dataclass
class QueryResult(Generic[T]):
    """Query result with pagination."""

    items: List[T]
    last_evaluated_key: Optional[Dict[str, Any]] = None
    count: int = 0
    scanned_count: int = 0


class DatabaseError(Exception):
    """Base database error."""

    pass


class ItemNotFoundError(DatabaseError):
    """Item not found error."""

    pass


class DuplicateItemError(DatabaseError):
    """Duplicate item error."""

    pass


class BaseRepository(ABC, Generic[T]):
    """Base repository with common DynamoDB operations."""

    def __init__(self, table_name: str) -> None:
        """Initialize repository with table name."""
        self.table_name = table_name
        self.table = aws_services.get_table(table_name)
        self.client = aws_services.dynamodb_client

    @abstractmethod
    def _to_model(self, item: Dict[str, Any]) -> T:
        """Convert DynamoDB item to domain model."""
        pass

    @abstractmethod
    def _to_item(self, model: T) -> Dict[str, Any]:
        """Convert domain model to DynamoDB item."""
        pass

    @tracer.trace_database_operation("get", "dynamodb")
    def get(self, key: Dict[str, str]) -> Optional[T]:
        """Get item by key."""
        try:
            response = self.table.get_item(Key=key)
            item = response.get("Item")

            if not item:
                return None

            return self._to_model(item)

        except ClientError as e:
            logger.log_error(e, {"table": self.table_name, "key": key})
            raise DatabaseError(f"Failed to get item: {e}")

    @tracer.trace_database_operation("put", "dynamodb")
    def put(self, model: T, key: Dict[str, str]) -> T:
        """Put item (create or update)."""
        try:
            item = self._to_item(model)
            item.update(key)

            self.table.put_item(Item=item)
            return model

        except ClientError as e:
            logger.log_error(e, {"table": self.table_name, "key": key})
            raise DatabaseError(f"Failed to put item: {e}")

    @tracer.trace_database_operation("delete", "dynamodb")
    def delete(self, key: Dict[str, str]) -> bool:
        """Delete item by key."""
        try:
            response = self.table.delete_item(Key=key)
            return response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200

        except ClientError as e:
            logger.log_error(e, {"table": self.table_name, "key": key})
            raise DatabaseError(f"Failed to delete item: {e}")

    @tracer.trace_database_operation("query", "dynamodb")
    def query(
        self,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> QueryResult[T]:
        """Query items."""
        try:
            query_kwargs: Dict[str, Any] = {
                "KeyConditionExpression": key_condition_expression,
                "ExpressionAttributeValues": expression_attribute_values,
            }

            if index_name:
                query_kwargs["IndexName"] = index_name

            if limit:
                query_kwargs["Limit"] = limit

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)

            items = [self._to_model(item) for item in response.get("Items", [])]

            return QueryResult(
                items=items,
                last_evaluated_key=response.get("LastEvaluatedKey"),
                count=response.get("Count", 0),
                scanned_count=response.get("ScannedCount", 0),
            )

        except ClientError as e:
            logger.log_error(
                e, {"table": self.table_name, "query": key_condition_expression}
            )
            raise DatabaseError(f"Failed to query items: {e}")
