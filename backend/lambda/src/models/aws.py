"""AWS-specific typed models."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class APIGatewayResponse(BaseModel):
    """Typed API Gateway response structure."""

    model_config = ConfigDict(from_attributes=True)

    statusCode: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    body: str = Field(..., description="Response body")
    isBase64Encoded: bool = Field(False, description="Whether body is base64 encoded")


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
