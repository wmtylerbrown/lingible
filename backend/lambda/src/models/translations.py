"""Translation models for GenZ slang translation app."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal
from pydantic import Field
from .base import LingibleBaseModel
from .users import UserTier


class TranslationDirection(str, Enum):
    """Translation direction enum."""

    GENZ_TO_ENGLISH = "genz_to_english"
    ENGLISH_TO_GENZ = "english_to_genz"


class TranslationStatus(str, Enum):
    """Translation status enum."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class TranslationRequest(LingibleBaseModel):
    """API request model for translation endpoint."""

    text: str = Field(
        ..., min_length=1, max_length=1000, description="Text to translate"
    )
    direction: TranslationDirection = Field(..., description="Translation direction")


class TranslationRequestInternal(LingibleBaseModel):
    """Internal request model for translation (includes user_id)."""

    text: str = Field(
        ..., min_length=1, max_length=1000, description="Text to translate"
    )
    direction: TranslationDirection = Field(..., description="Translation direction")
    user_id: Optional[str] = Field(None, description="User ID for usage tracking")


class Translation(LingibleBaseModel):
    """Domain model for translation records (DB storage and API responses)."""

    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: TranslationDirection = Field(
        ..., description="Translation direction used"
    )
    confidence_score: Optional[Decimal] = Field(
        None, ge=0.0, le=1.0, description="Translation confidence score"
    )
    translation_id: str = Field(..., description="Unique translation ID")
    created_at: datetime = Field(..., description="Translation timestamp")
    processing_time_ms: Optional[int] = Field(
        None, ge=0, description="Processing time in milliseconds"
    )
    model_used: Optional[str] = Field(None, description="AI model used for translation")

    # Usage data for response
    daily_used: int = Field(..., description="Total translations used today (after this translation)")
    daily_limit: int = Field(..., description="Daily translation limit")
    tier: UserTier = Field(..., description="User tier (free/premium)")



class TranslationHistory(LingibleBaseModel):
    """Domain model for translation history records (DB storage)."""

    translation_id: str = Field(..., description="Unique translation ID")
    user_id: str = Field(..., description="User ID")
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: TranslationDirection = Field(..., description="Translation direction")
    confidence_score: Optional[Decimal] = Field(
        None, description="Translation confidence score"
    )
    created_at: datetime = Field(..., description="Translation timestamp")
    model_used: Optional[str] = Field(None, description="AI model used")


class UsageLimit(LingibleBaseModel):
    """Model for usage limits (database storage)."""

    tier: UserTier = Field(..., description="User tier (free/premium) - source of truth for performance")
    daily_used: int = Field(0, ge=0, description="Current daily usage")
    reset_daily_at: datetime = Field(
        ..., description="When daily limit resets"
    )


class UsageLimitResponse(LingibleBaseModel):
    """Response model for usage limits (includes derived limits)."""

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_limit: int = Field(..., ge=0, description="Daily translation limit")
    daily_used: int = Field(..., ge=0, description="Current daily usage")
    daily_remaining: int = Field(..., ge=0, description="Daily usage remaining")
    reset_date: datetime = Field(..., description="Next daily reset date")


class TranslationError(LingibleBaseModel):
    """Model for translation errors."""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    translation_id: Optional[str] = Field(
        None, description="Translation ID if available"
    )
    retry_after: Optional[int] = Field(
        None, ge=0, description="Seconds to wait before retry"
    )


class BedrockRequest(LingibleBaseModel):
    """Model for Bedrock API request."""

    prompt: str = Field(..., description="Prompt for the AI model")
    max_tokens: int = Field(
        1000, ge=1, le=4000, description="Maximum tokens to generate"
    )
    temperature: Decimal = Field(
        Decimal("0.7"), ge=0.0, le=1.0, description="Temperature for generation"
    )
    top_p: Decimal = Field(Decimal("0.9"), ge=0.0, le=1.0, description="Top-p sampling parameter")


class BedrockResponse(LingibleBaseModel):
    """Model for Bedrock API response."""

    completion: str = Field(..., description="Generated completion")
    stop_reason: Optional[str] = Field(
        None, description="Reason for stopping generation"
    )
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")


# Service return types
class TranslationHistoryServiceResult(LingibleBaseModel):
    """Service return type for translation history operations."""

    translations: List[TranslationHistory] = Field(..., description="List of translation history items")
    total_count: int = Field(..., ge=0, description="Total number of translations")
    has_more: bool = Field(..., description="Whether there are more results available")
    last_evaluated_key: Optional[Dict[str, Any]] = Field(None, description="Pagination key for next request")
