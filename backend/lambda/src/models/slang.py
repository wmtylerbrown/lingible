"""
Slang translation models following Lingible patterns.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime
from pydantic import Field, field_validator
from enum import Enum
from .base import LingibleBaseModel


class AgeRating(str, Enum):
    """Age rating for content."""

    EVERYONE = "E"
    TEEN_13 = "T13"
    TEEN_16 = "T16"
    MATURE_18 = "M18"


class AgeFilterMode(str, Enum):
    """Age filter mode for content filtering."""

    SKIP = "skip"
    ANNOTATE = "annotate"


class PartOfSpeech(str, Enum):
    """Part of speech for slang terms."""

    PHRASE = "phrase"
    WORD = "word"
    ABBREVIATION = "abbr"
    ACRONYM = "acronym"
    EXPRESSION = "expression"
    SLANG = "slang"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    NOUN = "noun"
    VERB = "verb"
    INTERJECTION = "interjection"
    MEME = "meme"


class ApprovalStatus(str, Enum):
    """Approval status for slang terms."""

    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"
    DRAFT = "draft"


class SlangSubmissionStatus(str, Enum):
    """Validation status for slang submissions."""

    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    ADMIN_APPROVED = "admin_approved"


class ApprovalType(str, Enum):
    """Type of approval for submissions."""

    LLM_AUTO = "llm_auto"
    ADMIN_MANUAL = "admin_manual"
    COMMUNITY_VOTE = "community_vote"


class SourceType(str, Enum):
    """Source type for translation spans."""

    LEXEME = "lexeme"
    TEMPLATE = "template"


class SlangTerm(LingibleBaseModel):
    """Individual slang term with variants and metadata."""

    term: str = Field(..., description="Canonical term")
    variants: List[str] = Field(
        default_factory=list, description="Alternative spellings/forms"
    )
    pos: PartOfSpeech = Field(default=PartOfSpeech.PHRASE, description="Part of speech")
    gloss: str = Field(..., description="Translation/definition")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.APPROVED, description="Approval status"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score"
    )
    regions: List[str] = Field(default_factory=list, description="Regional usage")
    age_rating: AgeRating = Field(default=AgeRating.EVERYONE, description="Age rating")
    content_flags: List[str] = Field(
        default_factory=list, description="Content warnings"
    )
    first_seen: str = Field(..., description="First observation date")
    last_seen: str = Field(..., description="Last observation date")
    sources: Dict[str, int] = Field(
        default_factory=dict, description="Source frequency counts"
    )
    momentum: float = Field(default=1.0, ge=0.0, description="Trend momentum")
    categories: List[str] = Field(
        default_factory=list, description="Category classifications"
    )
    senses: Optional[List["SlangSense"]] = Field(
        default=None, description="Multiple senses/meanings"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class SlangSense(LingibleBaseModel):
    """Individual sense/meaning for a slang term."""

    id: str = Field(..., description="Unique sense identifier")
    gloss: str = Field(..., description="Definition for this sense")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence for this sense"
    )
    examples: List[str] = Field(
        default_factory=list, description="Examples for this sense"
    )
    context: Optional[str] = Field(default=None, description="Contextual usage notes")


class SlangLexicon(LingibleBaseModel):
    """Complete slang lexicon with metadata."""

    version: str = Field(..., description="Lexicon version")
    generated_at: str = Field(..., description="Generation timestamp")
    count: int = Field(..., ge=0, description="Number of terms")
    items: List[SlangTerm] = Field(..., description="Slang terms")


class TranslationSpan(LingibleBaseModel):
    """A span of text that matches a slang term or template."""

    start: int = Field(..., ge=0, description="Start position in text")
    end: int = Field(..., ge=0, description="End position in text")
    surface: str = Field(..., description="Surface form found in text")
    source: SourceType = Field(..., description="Source type")
    canonical: str = Field(..., description="Canonical form")
    gloss: Optional[str] = Field(default=None, description="Translation/definition")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Match confidence"
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, v: int, info) -> int:
        """Validate end position is after start position."""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be greater than start")
        return v

    @property
    def length(self) -> int:
        """Length of the span."""
        return self.end - self.start


class SlangTranslationResponse(LingibleBaseModel):
    """Response from slang translation LLM service."""

    translated: str = Field(..., description="Translated text")
    confidence: Decimal = Field(
        ...,
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Confidence score from LLM",
    )
    applied_terms: List[str] = Field(
        default_factory=list, description="Terms that were applied"
    )


class LLMValidationEvidence(LingibleBaseModel):
    """Evidence from web search for slang validation."""

    source: str = Field(..., description="Source URL or identifier")
    example: str = Field(..., description="Example usage found")


class LLMValidationResult(LingibleBaseModel):
    """Result from LLM validation of slang submission."""

    is_valid: bool = Field(..., description="Whether the slang term is valid")
    confidence: Decimal = Field(
        ...,
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Confidence score for validation",
    )
    evidence: List[LLMValidationEvidence] = Field(
        default_factory=list, description="Web evidence supporting validation"
    )
    recommended_definition: Optional[str] = Field(
        None, description="LLM-recommended definition if different from submission"
    )
    usage_score: int = Field(
        ..., ge=1, le=10, description="Widespread usage score (1-10)"
    )
    validated_at: datetime = Field(..., description="Validation timestamp")


class SubmissionContext(str, Enum):
    """Context for slang submission."""

    TRANSLATION_FAILURE = "translation_failure"
    MANUAL = "manual"


class SlangSubmission(LingibleBaseModel):
    """User-submitted slang term for review."""

    submission_id: str = Field(..., description="Unique submission identifier")
    user_id: str = Field(..., description="Submitting user ID")
    slang_term: str = Field(..., min_length=1, max_length=100, description="Slang term")
    meaning: str = Field(
        ..., min_length=1, max_length=500, description="Term meaning/definition"
    )
    example_usage: Optional[str] = Field(
        None, max_length=500, description="Example usage"
    )
    context: SubmissionContext = Field(..., description="Submission context")
    original_translation_id: Optional[str] = Field(
        None, description="Original translation ID if from failed translation"
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Review status"
    )
    created_at: datetime = Field(..., description="Submission timestamp")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    reviewed_by: Optional[str] = Field(None, description="Reviewer user ID")

    # Validation fields
    llm_validation_status: SlangSubmissionStatus = Field(
        default=SlangSubmissionStatus.PENDING_VALIDATION,
        description="LLM validation status",
    )
    llm_confidence_score: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Confidence score from LLM validation",
    )
    llm_validation_result: Optional[LLMValidationResult] = Field(
        None, description="Full LLM validation result"
    )

    # Approval tracking
    approval_type: Optional[ApprovalType] = Field(
        None, description="Type of approval received"
    )
    approved_by: Optional[str] = Field(
        None, description="Admin user ID if manually approved"
    )

    # Community voting
    upvotes: int = Field(default=0, ge=0, description="Number of upvotes")
    upvoted_by: List[str] = Field(
        default_factory=list, description="User IDs who upvoted"
    )


class SlangSubmissionRequest(LingibleBaseModel):
    """API request for submitting slang."""

    slang_term: str = Field(..., min_length=1, max_length=100, description="Slang term")
    meaning: str = Field(..., min_length=1, max_length=500, description="Term meaning")
    example_usage: Optional[str] = Field(
        None, max_length=500, description="Example usage"
    )
    context: SubmissionContext = Field(
        default=SubmissionContext.MANUAL, description="Submission context"
    )
    translation_id: Optional[str] = Field(
        None, description="Translation ID if from failed translation"
    )


class SlangSubmissionResponse(LingibleBaseModel):
    """API response for slang submission."""

    submission_id: str = Field(..., description="Created submission ID")
    status: ApprovalStatus = Field(..., description="Submission status")
    message: str = Field(..., description="Success message")
    created_at: datetime = Field(..., description="Submission timestamp")


class UpvoteResponse(LingibleBaseModel):
    """API response for upvoting a submission."""

    submission_id: str = Field(..., description="Upvoted submission ID")
    upvotes: int = Field(..., description="Total upvote count")
    message: str = Field(..., description="Success message")


class PendingSubmissionsResponse(LingibleBaseModel):
    """API response for pending submissions list."""

    submissions: List[SlangSubmission] = Field(..., description="List of submissions")
    total_count: int = Field(..., description="Total number of pending submissions")
    has_more: bool = Field(..., description="Whether more submissions exist")


class AdminApprovalResponse(LingibleBaseModel):
    """API response for admin approval/rejection."""

    submission_id: str = Field(..., description="Submission ID")
    status: ApprovalStatus = Field(..., description="New status")
    message: str = Field(..., description="Success message")
