"""Trending models for GenZ slang translation app."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING
from decimal import Decimal
from pydantic import Field
from .base import LingibleBaseModel

if TYPE_CHECKING:
    from .users import UserTier
else:
    from .users import UserTier


class TrendingCategory(str, Enum):
    """Categories for trending slang terms."""

    SLANG = "slang"
    MEME = "meme"
    EXPRESSION = "expression"
    HASHTAG = "hashtag"
    PHRASE = "phrase"


class TrendingTerm(LingibleBaseModel):
    """Trending slang term domain model."""

    # Core term data
    term: str = Field(..., description="The slang term or phrase")
    definition: str = Field(..., description="Definition or explanation of the term")
    category: TrendingCategory = Field(..., description="Category of the trending term")

    # Trending metrics
    popularity_score: Decimal = Field(
        ..., ge=0.0, le=100.0, description="Popularity score (0-100)"
    )
    search_count: int = Field(..., ge=0, description="Number of times searched")
    translation_count: int = Field(..., ge=0, description="Number of times translated")

    # Metadata
    first_seen: datetime = Field(..., description="When this term was first detected")
    last_updated: datetime = Field(..., description="Last time metrics were updated")
    is_active: bool = Field(True, description="Whether this term is currently trending")

    # Optional context
    example_usage: Optional[str] = Field(
        None, description="Example of how the term is used"
    )
    origin: Optional[str] = Field(None, description="Origin or source of the term")
    related_terms: List[str] = Field(
        default_factory=list, description="Related slang terms"
    )

    def to_api_response(
        self, user_tier: "UserTier" = UserTier.FREE
    ) -> "TrendingTermResponse":
        """Convert to API response model with tier-based data filtering."""
        # Free tier gets basic data
        if user_tier == UserTier.FREE:
            return TrendingTermResponse(
                term=self.term,
                definition=self.definition,
                category=self.category,
                popularity_score=self.popularity_score,
                search_count=0,  # Hide exact counts for free users
                translation_count=0,  # Hide exact counts for free users
                first_seen=self.first_seen,
                last_updated=self.last_updated,
                is_active=self.is_active,
                example_usage=None,  # Premium feature
                origin=None,  # Premium feature
                related_terms=[],  # Premium feature
            )
        else:  # Premium tier gets full data
            return TrendingTermResponse(
                term=self.term,
                definition=self.definition,
                category=self.category,
                popularity_score=self.popularity_score,
                search_count=self.search_count,
                translation_count=self.translation_count,
                first_seen=self.first_seen,
                last_updated=self.last_updated,
                is_active=self.is_active,
                example_usage=self.example_usage,
                origin=self.origin,
                related_terms=self.related_terms,
            )


class TrendingListResponse(LingibleBaseModel):
    """API response model for trending terms list."""

    terms: List["TrendingTermResponse"] = Field(
        ..., description="List of trending terms"
    )
    total_count: int = Field(..., description="Total number of trending terms")
    last_updated: datetime = Field(
        ..., description="When the trending data was last updated"
    )
    category_filter: Optional[TrendingCategory] = Field(
        None, description="Applied category filter"
    )


class TrendingTermResponse(LingibleBaseModel):
    """API response model for individual trending term."""

    term: str = Field(..., description="The slang term or phrase")
    definition: str = Field(..., description="Definition or explanation of the term")
    category: TrendingCategory = Field(..., description="Category of the trending term")
    popularity_score: Decimal = Field(..., description="Popularity score (0-100)")
    search_count: int = Field(..., description="Number of times searched")
    translation_count: int = Field(..., description="Number of times translated")
    first_seen: datetime = Field(..., description="When this term was first detected")
    last_updated: datetime = Field(..., description="Last time metrics were updated")
    is_active: bool = Field(..., description="Whether this term is currently trending")
    example_usage: Optional[str] = Field(
        None, description="Example of how the term is used"
    )
    origin: Optional[str] = Field(None, description="Origin or source of the term")
    related_terms: List[str] = Field(..., description="Related slang terms")


class TrendingJobRequest(LingibleBaseModel):
    """Request model for trending data generation job."""

    job_type: str = Field(..., description="Type of trending job to run")
    source: str = Field(..., description="Data source for trending analysis")
    parameters: dict = Field(
        default_factory=dict, description="Job-specific parameters"
    )
    scheduled_at: Optional[datetime] = Field(None, description="When to run the job")


class TrendingJobResponse(LingibleBaseModel):
    """Response model for trending job execution."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job execution status")
    terms_processed: int = Field(..., description="Number of terms processed")
    terms_added: int = Field(..., description="Number of new terms added")
    terms_updated: int = Field(..., description="Number of existing terms updated")
    execution_time_seconds: Decimal = Field(
        ..., description="Job execution time in seconds"
    )
    started_at: datetime = Field(..., description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    error_message: Optional[str] = Field(
        None, description="Error message if job failed"
    )
