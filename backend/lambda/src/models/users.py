"""User models for GenZ slang translation app."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# Domain Models
class UserTier(Enum):
    """User subscription tiers."""

    FREE = "free"
    PREMIUM = "premium"


class UserStatus(Enum):
    """User account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class User(BaseModel):
    """User domain model."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        use_enum_values=True,  # Serialize enums as their values
    )

    # Core user data (from Cognito)
    user_id: str = Field(..., description="Cognito user ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Cognito username")

    # App-specific data
    tier: UserTier = Field(UserTier.FREE, description="User subscription tier")
    status: UserStatus = Field(UserStatus.ACTIVE, description="User account status")

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Account creation date"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update date",
    )

    def to_api_response(self) -> "UserResponse":
        """Convert to API response model."""
        return UserResponse(
            user_id=self.user_id,
            email=self.email,
            username=self.username,
            tier=self.tier,
            status=self.status,
            created_at=self.created_at.isoformat(),
        )


# API Models
class UserResponse(BaseModel):
    """API response model for user profile data."""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    tier: UserTier = Field(..., description="User tier")
    status: UserStatus = Field(..., description="Account status")

    created_at: str = Field(..., description="Account creation date (ISO format)")


class UserUsageResponse(BaseModel):
    """User usage API response - dynamic data, not cacheable."""

    model_config = ConfigDict(from_attributes=True)

    tier: UserTier = Field(..., description="User tier (free/premium)")
    daily_limit: int = Field(..., description="Daily translation limit")
    daily_used: int = Field(..., description="Translations used today")
    daily_remaining: int = Field(..., description="Translations remaining today")
    reset_date: datetime = Field(..., description="Next daily reset date")
