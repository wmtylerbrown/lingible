"""
Slang translation models following Lingible patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from decimal import Decimal
from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from .base import LingibleBaseModel
from .quiz import QuizCategory, QuizDifficulty


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
    first_seen: Optional[str] = Field(
        default=None, description="First observation date (YYYY-MM-DD)"
    )
    last_seen: Optional[str] = Field(
        default=None, description="Most recent observation date (YYYY-MM-DD)"
    )
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
    # Quiz metadata
    is_quiz_eligible: bool = Field(
        default=False, description="Whether this term is eligible for quizzes"
    )
    quiz_category: QuizCategory = Field(
        default=QuizCategory.GENERAL, description="Quiz category classification"
    )
    quiz_difficulty: QuizDifficulty = Field(
        default=QuizDifficulty.BEGINNER, description="Quiz difficulty classification"
    )
    first_attested: Optional[str] = Field(
        default=None, description="First attested date for quiz usage"
    )
    first_attested_confidence: Optional[str] = Field(
        default=None, description="Confidence in first attested metadata"
    )
    attestation_note: Optional[str] = Field(
        default=None, description="Additional attestation notes"
    )
    quiz_accuracy_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Historical quiz accuracy rate for this term",
    )
    times_in_quiz: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of times the term has appeared in quizzes",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator(
        "variants",
        "examples",
        "tags",
        "regions",
        "content_flags",
        "categories",
        mode="before",
    )
    @classmethod
    def ensure_list_of_strings(cls, value: Optional[Any]) -> List[str]:
        """Ensure list-based fields are normalized to lists of strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, (set, tuple)):
            return [str(item) for item in value if item is not None]
        return [str(value)]

    @field_validator("sources", mode="before")
    @classmethod
    def ensure_sources(cls, value: Optional[Any]) -> Dict[str, int]:
        """Normalize sources mapping to str->int."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            return {}
        normalized: Dict[str, int] = {}
        for key, raw in value.items():
            if raw is None:
                continue
            try:
                normalized[str(key)] = int(raw)
            except (TypeError, ValueError):
                continue
        return normalized

    @field_validator("pos", mode="before")
    @classmethod
    def ensure_part_of_speech(cls, value: Optional[Any]) -> PartOfSpeech:
        if isinstance(value, PartOfSpeech):
            return value
        if value is None or value == "":
            return PartOfSpeech.PHRASE
        try:
            return PartOfSpeech(str(value))
        except ValueError:
            return PartOfSpeech.PHRASE

    @field_validator("age_rating", mode="before")
    @classmethod
    def ensure_age_rating(cls, value: Optional[Any]) -> AgeRating:
        if isinstance(value, AgeRating):
            return value
        if value is None or value == "":
            return AgeRating.EVERYONE
        try:
            return AgeRating(str(value))
        except ValueError:
            return AgeRating.EVERYONE

    @field_validator("status", mode="before")
    @classmethod
    def ensure_status(cls, value: Optional[Any]) -> ApprovalStatus:
        if isinstance(value, ApprovalStatus):
            return value
        if value is None or value == "":
            return ApprovalStatus.APPROVED
        try:
            return ApprovalStatus(str(value))
        except ValueError:
            return ApprovalStatus.APPROVED

    @field_validator("momentum", mode="before")
    @classmethod
    def ensure_float(cls, value: Optional[Any]) -> float:
        """Ensure float fields accept numeric strings/decimals."""
        if value is None:
            return 1.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError("momentum must be convertible to float")

    @field_validator("quiz_accuracy_rate", mode="before")
    @classmethod
    def validate_quiz_accuracy(cls, value: Optional[Any]) -> Optional[float]:
        """Ensure quiz accuracy is a float when provided."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError("quiz_accuracy_rate must be convertible to float")

    @field_validator("times_in_quiz", mode="before")
    @classmethod
    def validate_times_in_quiz(cls, value: Optional[Any]) -> Optional[int]:
        """Ensure times_in_quiz is an int when provided."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError("times_in_quiz must be convertible to int")

    @field_validator("quiz_category", mode="before")
    @classmethod
    def validate_quiz_category(cls, value: Any) -> QuizCategory:
        """Coerce quiz category into QuizCategory enum."""
        if isinstance(value, QuizCategory):
            return value
        if value is None or value == "":
            return QuizCategory.GENERAL
        if hasattr(value, "value"):
            return QuizCategory(value.value)
        return QuizCategory(str(value))

    @field_validator("quiz_difficulty", mode="before")
    @classmethod
    def validate_quiz_difficulty(cls, value: Any) -> QuizDifficulty:
        """Coerce quiz difficulty into QuizDifficulty enum."""
        if isinstance(value, QuizDifficulty):
            return value
        if value is None or value == "":
            return QuizDifficulty.BEGINNER
        if hasattr(value, "value"):
            return QuizDifficulty(value.value)
        return QuizDifficulty(str(value))

    @property
    def slang_term(self) -> str:
        """Canonical slang term alias."""
        return self.term

    @property
    def meaning(self) -> str:
        """Convenience alias for gloss."""
        return self.gloss

    @property
    def example_usage(self) -> Optional[str]:
        """Return the primary example usage if available."""
        return self.examples[0] if self.examples else None


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
