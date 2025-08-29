"""Typed event models for Lambda handlers."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .translations import TranslationRequestBody
from .aws import APIGatewayResponse


class TranslationEvent(BaseModel):
    """Typed event for translation handler."""
    
    # API Gateway event data
    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: TranslationRequestBody = Field(..., description="Parsed request body")
    
    # Extracted user info (if available)
    user_id: Optional[str] = Field(None, description="User ID from Cognito token")
    username: Optional[str] = Field(None, description="Username from Cognito token")
    
    # Request metadata
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class UserProfileEvent(BaseModel):
    """Typed event for user profile handler."""
    
    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: Optional[str] = Field(None, description="User ID from Cognito token")
    username: Optional[str] = Field(None, description="Username from Cognito token")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class TranslationHistoryEvent(BaseModel):
    """Typed event for translation history handler."""
    
    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: Optional[str] = Field(None, description="User ID from Cognito token")
    username: Optional[str] = Field(None, description="Username from Cognito token")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    
    # Query parameters
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of items to return")
    offset: Optional[int] = Field(0, ge=0, description="Number of items to skip")
