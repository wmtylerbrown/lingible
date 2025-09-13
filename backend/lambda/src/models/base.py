"""Base API response models."""

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_serializer


class HTTPStatus(Enum):
    """HTTP status codes for API responses."""

    # Success codes
    OK = 200
    CREATED = 201
    NO_CONTENT = 204

    # Client error codes
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # Server error codes
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ErrorCode(Enum):
    """Application-specific error codes."""

    # Authentication errors
    INVALID_TOKEN = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    INSUFFICIENT_PERMISSIONS = "AUTH_003"

    # Validation errors
    INVALID_INPUT = "VAL_001"
    MISSING_REQUIRED_FIELD = "VAL_002"
    INVALID_FORMAT = "VAL_003"

    # Resource errors
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_CONFLICT = "RES_003"

    # Business logic errors
    USAGE_LIMIT_EXCEEDED = "BIZ_001"
    INSUFFICIENT_CREDITS = "BIZ_002"
    SERVICE_UNAVAILABLE = "BIZ_003"

    # System errors
    DATABASE_ERROR = "SYS_001"
    EXTERNAL_SERVICE_ERROR = "SYS_002"
    INTERNAL_ERROR = "SYS_003"

    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "RATE_001"


class LingibleBaseModel(BaseModel):
    """Base model for all Lingible models with automatic serialization handling."""

    class Config:
        """Pydantic configuration for consistent serialization."""
        # Use enum values instead of enum objects
        use_enum_values = True
        # Validate assignment to catch type errors early
        validate_assignment = True
        # Allow population by field name or alias
        populate_by_name = True
        # Allow creation from ORM objects (future-proofing)
        from_attributes = True
        # Use custom serializers for complex types
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serializer that handles Decimal and datetime objects automatically."""
        result: Dict[str, Any] = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Decimal):
                result[field_name] = float(field_value)
            elif isinstance(field_value, datetime):
                result[field_name] = field_value.isoformat()
            else:
                result[field_name] = field_value
        return result

    def to_json(self) -> str:
        """Convert model to JSON string with proper serialization."""
        return json.dumps(self.serialize_model())

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with proper serialization."""
        return self.serialize_model()


class BaseResponse(LingibleBaseModel):
    """Base API response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(..., description="Response timestamp")


class ErrorResponse(LingibleBaseModel):
    """Standardized error response model."""

    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Application-specific error code")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class PaginationParams(BaseModel):
    """Pagination parameters for list requests."""

    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )


class PaginatedResponse(LingibleBaseModel):
    """Paginated response model."""

    success: bool = Field(True, description="Whether the request was successful")
    data: List[Dict[str, Any]] = Field(..., description="List of items")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(LingibleBaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status (healthy, unhealthy, etc.)")
