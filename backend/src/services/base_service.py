"""Base service pattern for business logic."""

from typing import Generic, TypeVar, Optional, Dict, Any
from abc import ABC, abstractmethod

from ..utils.logging import logger
from ..utils.tracing import tracer
from ..repositories.base_repository import BaseRepository, QueryResult, DatabaseError


T = TypeVar("T")
R = TypeVar("R")


class ServiceError(Exception):
    """Base service error."""

    pass


class ValidationError(ServiceError):
    """Validation error."""

    pass


class AuthorizationError(ServiceError):
    """Authorization error."""

    pass


class BaseService(ABC, Generic[T, R]):
    """Base service with common business logic patterns."""

    def __init__(self, repository: BaseRepository[T]) -> None:
        """Initialize service with repository."""
        self.repository = repository

    @abstractmethod
    def _validate_create(self, data: R) -> None:
        """Validate data for creation."""
        pass

    @abstractmethod
    def _validate_update(self, data: R) -> None:
        """Validate data for update."""
        pass

    @abstractmethod
    def _authorize_access(self, user_id: str, resource_id: str) -> bool:
        """Authorize user access to resource."""
        pass

    @tracer.trace_method("service_create")
    def create(self, data: R, user_id: str) -> T:
        """Create new item with validation and authorization."""
        try:
            # Validate input
            self._validate_create(data)

            # Create domain model
            model = self._create_model(data, user_id)

            # Save to repository
            key = self._get_key(model, user_id)
            result = self.repository.put(model, key)

            # Log business event
            logger.log_business_event(
                "item_created",
                {
                    "user_id": user_id,
                    "item_id": self._get_item_id(model),
                    "item_type": type(model).__name__,
                },
            )

            return result

        except ValidationError as e:
            logger.log_error(e, {"user_id": user_id, "data": str(data)})
            raise
        except DatabaseError as e:
            logger.log_error(e, {"user_id": user_id, "data": str(data)})
            raise ServiceError(f"Failed to create item: {e}")

    @tracer.trace_method("service_get")
    def get(self, item_id: str, user_id: str) -> Optional[T]:
        """Get item with authorization."""
        try:
            # Check authorization
            if not self._authorize_access(user_id, item_id):
                raise AuthorizationError(
                    f"User {user_id} not authorized to access item {item_id}"
                )

            # Get from repository
            key = self._get_key_by_id(item_id, user_id)
            return self.repository.get(key)

        except AuthorizationError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise
        except DatabaseError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise ServiceError(f"Failed to get item: {e}")

    @tracer.trace_method("service_update")
    def update(self, item_id: str, data: R, user_id: str) -> Optional[T]:
        """Update item with validation and authorization."""
        try:
            # Check authorization
            if not self._authorize_access(user_id, item_id):
                raise AuthorizationError(
                    f"User {user_id} not authorized to update item {item_id}"
                )

            # Validate input
            self._validate_update(data)

            # Get existing item
            key = self._get_key_by_id(item_id, user_id)
            existing = self.repository.get(key)

            if not existing:
                return None

            # Update model
            updated_model = self._update_model(existing, data)

            # Save to repository
            result = self.repository.put(updated_model, key)

            # Log business event
            logger.log_business_event(
                "item_updated",
                {
                    "user_id": user_id,
                    "item_id": item_id,
                    "item_type": type(result).__name__,
                },
            )

            return result

        except AuthorizationError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise
        except ValidationError as e:
            logger.log_error(
                e, {"user_id": user_id, "item_id": item_id, "data": str(data)}
            )
            raise
        except DatabaseError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise ServiceError(f"Failed to update item: {e}")

    @tracer.trace_method("service_delete")
    def delete(self, item_id: str, user_id: str) -> bool:
        """Delete item with authorization."""
        try:
            # Check authorization
            if not self._authorize_access(user_id, item_id):
                raise AuthorizationError(
                    f"User {user_id} not authorized to delete item {item_id}"
                )

            # Delete from repository
            key = self._get_key_by_id(item_id, user_id)
            result = self.repository.delete(key)

            if result:
                # Log business event
                logger.log_business_event(
                    "item_deleted", {"user_id": user_id, "item_id": item_id}
                )

            return result

        except AuthorizationError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise
        except DatabaseError as e:
            logger.log_error(e, {"user_id": user_id, "item_id": item_id})
            raise ServiceError(f"Failed to delete item: {e}")

    @tracer.trace_method("service_list")
    def list_by_user(
        self,
        user_id: str,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> QueryResult[T]:
        """List items for user with pagination."""
        try:
            # Query repository
            key_condition = "SK = :user_id"
            expression_values = {":user_id": f"USER#{user_id}"}

            return self.repository.query(
                key_condition_expression=key_condition,
                expression_attribute_values=expression_values,
                index_name="user_items_index",
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )

        except DatabaseError as e:
            logger.log_error(e, {"user_id": user_id})
            raise ServiceError(f"Failed to list items: {e}")

    @abstractmethod
    def _create_model(self, data: R, user_id: str) -> T:
        """Create domain model from data."""
        pass

    @abstractmethod
    def _update_model(self, existing: T, data: R) -> T:
        """Update existing model with data."""
        pass

    @abstractmethod
    def _get_key(self, model: T, user_id: str) -> Any:
        """Get DynamoDB key for model."""
        pass

    @abstractmethod
    def _get_key_by_id(self, item_id: str, user_id: str) -> Any:
        """Get DynamoDB key by item ID."""
        pass

    @abstractmethod
    def _get_item_id(self, model: T) -> str:
        """Get item ID from model."""
        pass
