"""Translation models for GenZ slang translation app."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

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


class TranslationRequest(BaseModel):
    """API request model for translation endpoint."""

    text: str = Field(
        ..., min_length=1, max_length=1000, description="Text to translate"
    )
    direction: TranslationDirection = Field(..., description="Translation direction")


class TranslationRequestInternal(BaseModel):
    """Internal request model for translation (includes user_id)."""

    model_config = ConfigDict(from_attributes=True)

    text: str = Field(
        ..., min_length=1, max_length=1000, description="Text to translate"
    )
    direction: TranslationDirection = Field(..., description="Translation direction")
    user_id: Optional[str] = Field(None, description="User ID for usage tracking")


class Translation(BaseModel):
    """Domain model for translation records (DB storage and API responses)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,  # Serialize enums as their values
    )

    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: TranslationDirection = Field(
        ..., description="Translation direction used"
    )
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Translation confidence score"
    )
    translation_id: str = Field(..., description="Unique translation ID")
    created_at: datetime = Field(..., description="Translation timestamp")
    processing_time_ms: Optional[int] = Field(
        None, ge=0, description="Processing time in milliseconds"
    )
    model_used: Optional[str] = Field(None, description="AI model used for translation")

    def to_api_response(self) -> "TranslationResponse":
        """Convert to API response model."""
        return TranslationResponse(
            translation_id=self.translation_id,
            original_text=self.original_text,
            translated_text=self.translated_text,
            direction=self.direction.value,  # Convert enum to string
            confidence_score=self.confidence_score,
            created_at=self.created_at.isoformat(),  # Convert to ISO string
            processing_time_ms=self.processing_time_ms,
            model_used=self.model_used,
        )


class TranslationResponse(BaseModel):
    """API response model for translation data."""

    translation_id: str = Field(..., description="Unique translation ID")
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: str = Field(..., description="Translation direction")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Translation confidence score"
    )
    created_at: str = Field(..., description="Translation timestamp (ISO format)")
    processing_time_ms: Optional[int] = Field(
        None, ge=0, description="Processing time in milliseconds"
    )
    model_used: Optional[str] = Field(None, description="AI model used for translation")


class TranslationHistory(BaseModel):
    """Domain model for translation history records (DB storage)."""

    model_config = ConfigDict(from_attributes=True)

    translation_id: str = Field(..., description="Unique translation ID")
    user_id: str = Field(..., description="User ID")
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: TranslationDirection = Field(..., description="Translation direction")
    confidence_score: Optional[float] = Field(
        None, description="Translation confidence score"
    )
    created_at: datetime = Field(..., description="Translation timestamp")
    model_used: Optional[str] = Field(None, description="AI model used")

    def to_api_response(self) -> "TranslationHistoryItemResponse":
        """Convert to API response model."""
        return TranslationHistoryItemResponse(
            translation_id=self.translation_id,
            user_id=self.user_id,
            original_text=self.original_text,
            translated_text=self.translated_text,
            direction=self.direction.value,  # Convert enum to string
            confidence_score=self.confidence_score,
            created_at=self.created_at.isoformat(),  # Convert to ISO string
            model_used=self.model_used,
        )


class TranslationHistoryItemResponse(BaseModel):
    """API response model for individual translation history items."""

    translation_id: str = Field(..., description="Unique translation ID")
    user_id: str = Field(..., description="User ID")
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    direction: str = Field(..., description="Translation direction")
    confidence_score: Optional[float] = Field(
        None, description="Translation confidence score"
    )
    created_at: str = Field(..., description="Translation timestamp (ISO format)")
    model_used: Optional[str] = Field(None, description="AI model used")


class TranslationHistoryResponse(BaseModel):
    """Response model for translation history."""

    model_config = ConfigDict(from_attributes=True)

    translations: List[TranslationHistoryItemResponse] = Field(
        ..., description="List of translations"
    )
    total_count: int = Field(..., ge=0, description="Total number of translations")
    has_more: bool = Field(
        ..., description="Whether there are more translations to load"
    )


class UsageLimit(BaseModel):
    """Model for usage limits (database storage)."""

    model_config = ConfigDict(from_attributes=True)

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_used: int = Field(0, ge=0, description="Current daily usage")
    reset_daily_at: Optional[datetime] = Field(
        None, description="When daily limit resets"
    )


class UsageLimitResponse(BaseModel):
    """Response model for usage limits (includes derived limits)."""

    model_config = ConfigDict(from_attributes=True)

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_limit: int = Field(..., ge=0, description="Daily translation limit")
    daily_used: int = Field(..., ge=0, description="Current daily usage")
    daily_remaining: int = Field(..., ge=0, description="Daily usage remaining")
    reset_date: datetime = Field(..., description="Next daily reset date")


class TranslationError(BaseModel):
    """Model for translation errors."""

    model_config = ConfigDict(from_attributes=True)

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    translation_id: Optional[str] = Field(
        None, description="Translation ID if available"
    )
    retry_after: Optional[int] = Field(
        None, ge=0, description="Seconds to wait before retry"
    )


class BedrockRequest(BaseModel):
    """Model for Bedrock API request."""

    model_config = ConfigDict(from_attributes=True)

    prompt: str = Field(..., description="Prompt for the AI model")
    max_tokens: int = Field(
        1000, ge=1, le=4000, description="Maximum tokens to generate"
    )
    temperature: float = Field(
        0.7, ge=0.0, le=1.0, description="Temperature for generation"
    )
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-p sampling parameter")


class BedrockResponse(BaseModel):
    """Model for Bedrock API response."""

    model_config = ConfigDict(from_attributes=True)

    completion: str = Field(..., description="Generated completion")
    stop_reason: Optional[str] = Field(
        None, description="Reason for stopping generation"
    )
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
