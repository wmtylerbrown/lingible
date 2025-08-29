"""AWS-specific typed models using Lambda Powertools built-in models."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Import Lambda Powertools models
# from aws_lambda_powertools.utilities.parser.models import APIGatewayProxyEventModel


# Custom models for responses and other specific needs
class APIGatewayResponse(BaseModel):
    """Typed API Gateway response structure."""

    model_config = ConfigDict(from_attributes=True)

    statusCode: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    body: str = Field(..., description="Response body")
    isBase64Encoded: bool = Field(False, description="Whether body is base64 encoded")


# Cognito Models (for our specific use case)
class CognitoUserInfo(BaseModel):
    """Typed Cognito user information for our app."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., description="Cognito user ID")
    username: str = Field(..., description="Cognito username")
    email: Optional[str] = Field(None, description="User email")
    attributes: Dict[str, str] = Field(
        default_factory=dict, description="User attributes"
    )

    @classmethod
    def from_cognito_response(cls, response: Dict[str, Any]) -> "CognitoUserInfo":
        """Create from Cognito get_user response."""
        attributes = {}
        for attr in response.get("UserAttributes", []):
            attributes[attr["Name"]] = attr["Value"]

        return cls(
            user_id=response["Username"],
            username=response["Username"],
            email=attributes.get("email"),
            attributes=attributes,
        )


# DynamoDB Models (for our specific use case)
class DynamoDBKey(BaseModel):
    """Typed DynamoDB key structure."""

    model_config = ConfigDict(from_attributes=True)

    PK: str = Field(..., description="Partition key")
    SK: str = Field(..., description="Sort key")


class DynamoDBItem(BaseModel):
    """Typed DynamoDB item structure."""

    model_config = ConfigDict(from_attributes=True)

    # Core DynamoDB fields
    PK: str = Field(..., description="Partition key")
    SK: str = Field(..., description="Sort key")

    # Common metadata fields
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    ttl: Optional[int] = Field(None, description="Time to live")

    # Additional fields (will be validated by specific models)
    data: Dict[str, Any] = Field(default_factory=dict, description="Item data")


class DynamoDBQueryParams(BaseModel):
    """Typed DynamoDB query parameters."""

    model_config = ConfigDict(from_attributes=True)

    key_condition_expression: str = Field(..., description="Key condition expression")
    expression_attribute_values: Dict[str, Any] = Field(
        ..., description="Expression attribute values"
    )
    index_name: Optional[str] = Field(None, description="Index name")
    limit: Optional[int] = Field(None, description="Query limit")
    last_evaluated_key: Optional[Dict[str, Any]] = Field(
        None, description="Last evaluated key"
    )


# Logging Models
class LogContext(BaseModel):
    """Typed logging context."""

    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[str] = Field(None, description="User ID")
    request_id: Optional[str] = Field(None, description="Request ID")
    table: Optional[str] = Field(None, description="Database table")
    operation: Optional[str] = Field(None, description="Operation type")
    error_type: Optional[str] = Field(None, description="Error type")
    error_message: Optional[str] = Field(None, description="Error message")
    additional_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context data"
    )


class BusinessEventData(BaseModel):
    """Typed business event data."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(..., description="Event type")
    user_id: Optional[str] = Field(None, description="User ID")
    item_id: Optional[str] = Field(None, description="Item ID")
    item_type: Optional[str] = Field(None, description="Item type")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
