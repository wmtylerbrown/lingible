"""Trending service for trending terms business logic."""

from datetime import datetime, timezone
from typing import List, Optional

from models.trending import (
    TrendingTerm,
    TrendingCategory,
    TrendingListResponse,
    TrendingJobRequest,
    TrendingJobResponse,
)
from utils.logging import logger
from utils.tracing import tracer
from utils.exceptions import ValidationError
from repositories.trending_repository import TrendingRepository


class TrendingService:
    """Service for trending terms business logic."""

    def __init__(self) -> None:
        """Initialize trending service."""
        self.repository = TrendingRepository()

    @tracer.trace_method("get_trending_terms")
    def get_trending_terms(
        self,
        limit: int = 50,
        category: Optional[TrendingCategory] = None,
        active_only: bool = True,
        user_tier: str = "free",
    ) -> TrendingListResponse:
        """Get trending terms with optional filtering and tier-based features."""
        try:
            # Apply tier-based limits
            if user_tier == "free":
                # Free users get limited access
                if limit > 10:
                    limit = 10
                # Free users can only access 'slang' category
                if category and category != TrendingCategory.SLANG:
                    raise ValidationError("Category filtering is a premium feature. Free users can only access 'slang' category.")
            else:
                # Premium users get full access
                if limit < 1 or limit > 100:
                    raise ValidationError("Limit must be between 1 and 100")

            # Get trending terms from repository
            terms = self.repository.get_trending_terms(
                limit=limit,
                category=category,
                active_only=active_only,
            )

            # Convert to API response models with tier-based filtering
            term_responses = [term.to_api_response(user_tier) for term in terms]

            # Get total count for stats
            stats = self.repository.get_trending_stats()
            total_count = stats.get("total_active_terms", 0)

            return TrendingListResponse(
                terms=term_responses,
                total_count=total_count,
                last_updated=datetime.now(timezone.utc).isoformat(),
                category_filter=category,
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_trending_terms",
                    "limit": limit,
                    "category": category.value if category else None,
                },
            )
            raise

    @tracer.trace_method("get_trending_term")
    def get_trending_term(self, term: str) -> Optional[TrendingTerm]:
        """Get a specific trending term."""
        try:
            if not term or not term.strip():
                raise ValidationError("Term cannot be empty")

            return self.repository.get_trending_term(term.strip())

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_trending_term",
                    "term": term,
                },
            )
            raise

    @tracer.trace_method("create_trending_term")
    def create_trending_term(
        self,
        term: str,
        definition: str,
        category: TrendingCategory,
        popularity_score: float = 0.0,
        example_usage: Optional[str] = None,
        origin: Optional[str] = None,
        related_terms: Optional[List[str]] = None,
    ) -> TrendingTerm:
        """Create a new trending term."""
        try:
            if not term or not term.strip():
                raise ValidationError("Term cannot be empty")

            if not definition or not definition.strip():
                raise ValidationError("Definition cannot be empty")

            if popularity_score < 0.0 or popularity_score > 100.0:
                raise ValidationError("Popularity score must be between 0 and 100")

            # Check if term already exists
            existing_term = self.repository.get_trending_term(term.strip())
            if existing_term:
                raise ValidationError(f"Trending term '{term}' already exists")

            now = datetime.now(timezone.utc)
            trending_term = TrendingTerm(
                term=term.strip(),
                definition=definition.strip(),
                category=category,
                popularity_score=popularity_score,
                search_count=0,
                translation_count=0,
                first_seen=now,
                last_updated=now,
                is_active=True,
                example_usage=example_usage.strip() if example_usage else None,
                origin=origin.strip() if origin else None,
                related_terms=related_terms or [],
            )

            success = self.repository.create_trending_term(trending_term)
            if not success:
                raise ValidationError("Failed to create trending term")

            logger.log_business_event(
                "trending_term_created",
                {
                    "term": trending_term.term,
                    "category": category.value,
                    "popularity_score": popularity_score,
                },
            )

            return trending_term

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_trending_term",
                    "term": term,
                },
            )
            raise

    @tracer.trace_method("update_trending_term")
    def update_trending_term(
        self,
        term: str,
        definition: Optional[str] = None,
        category: Optional[TrendingCategory] = None,
        popularity_score: Optional[float] = None,
        is_active: Optional[bool] = None,
        example_usage: Optional[str] = None,
        origin: Optional[str] = None,
        related_terms: Optional[List[str]] = None,
    ) -> TrendingTerm:
        """Update an existing trending term."""
        try:
            if not term or not term.strip():
                raise ValidationError("Term cannot be empty")

            # Get existing term
            existing_term = self.repository.get_trending_term(term.strip())
            if not existing_term:
                raise ValidationError(f"Trending term '{term}' not found")

            # Update fields if provided
            if definition is not None:
                if not definition.strip():
                    raise ValidationError("Definition cannot be empty")
                existing_term.definition = definition.strip()

            if category is not None:
                existing_term.category = category

            if popularity_score is not None:
                if popularity_score < 0.0 or popularity_score > 100.0:
                    raise ValidationError("Popularity score must be between 0 and 100")
                existing_term.popularity_score = popularity_score

            if is_active is not None:
                existing_term.is_active = is_active

            if example_usage is not None:
                existing_term.example_usage = example_usage.strip() if example_usage else None

            if origin is not None:
                existing_term.origin = origin.strip() if origin else None

            if related_terms is not None:
                existing_term.related_terms = related_terms

            # Update timestamp
            existing_term.last_updated = datetime.now(timezone.utc)

            success = self.repository.update_trending_term(existing_term)
            if not success:
                raise ValidationError("Failed to update trending term")

            logger.log_business_event(
                "trending_term_updated",
                {
                    "term": existing_term.term,
                    "category": existing_term.category.value,
                },
            )

            return existing_term

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_trending_term",
                    "term": term,
                },
            )
            raise

    @tracer.trace_method("increment_search_count")
    def increment_search_count(self, term: str) -> bool:
        """Increment search count for a trending term."""
        try:
            if not term or not term.strip():
                return False

            return self.repository.increment_search_count(term.strip())

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_search_count",
                    "term": term,
                },
            )
            return False

    @tracer.trace_method("increment_translation_count")
    def increment_translation_count(self, term: str) -> bool:
        """Increment translation count for a trending term."""
        try:
            if not term or not term.strip():
                return False

            return self.repository.increment_translation_count(term.strip())

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_translation_count",
                    "term": term,
                },
            )
            return False

    @tracer.trace_method("run_trending_job")
    def run_trending_job(self, job_request: TrendingJobRequest) -> TrendingJobResponse:
        """Run a trending data generation job."""
        try:
            job_id = f"trending_job_{int(datetime.now(timezone.utc).timestamp())}"
            start_time = datetime.now(timezone.utc)

            logger.log_business_event(
                "trending_job_started",
                {
                    "job_id": job_id,
                    "job_type": job_request.job_type,
                    "source": job_request.source,
                },
            )

            terms_processed = 0
            terms_added = 0
            terms_updated = 0

            # Simulate trending data generation based on job type
            if job_request.job_type == "gen_z_slang_analysis":
                # This would typically call external APIs or analyze existing data
                # For now, we'll create some sample trending terms
                sample_terms = self._generate_sample_trending_terms()

                for term_data in sample_terms:
                    terms_processed += 1

                    # Check if term already exists
                    existing_term = self.repository.get_trending_term(term_data["term"])

                    if existing_term:
                        # Update existing term
                        existing_term.popularity_score = term_data["popularity_score"]
                        existing_term.last_updated = datetime.now(timezone.utc)
                        success = self.repository.update_trending_term(existing_term)
                        if success:
                            terms_updated += 1
                    else:
                        # Create new term
                        new_term = TrendingTerm(
                            term=term_data["term"],
                            definition=term_data["definition"],
                            category=term_data["category"],
                            popularity_score=term_data["popularity_score"],
                            search_count=0,
                            translation_count=0,
                            first_seen=datetime.now(timezone.utc),
                            last_updated=datetime.now(timezone.utc),
                            is_active=True,
                            example_usage=term_data.get("example_usage"),
                            origin=term_data.get("origin"),
                            related_terms=term_data.get("related_terms", []),
                        )
                        success = self.repository.create_trending_term(new_term)
                        if success:
                            terms_added += 1

            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()

            logger.log_business_event(
                "trending_job_completed",
                {
                    "job_id": job_id,
                    "terms_processed": terms_processed,
                    "terms_added": terms_added,
                    "terms_updated": terms_updated,
                    "execution_time_seconds": execution_time,
                },
            )

            return TrendingJobResponse(
                job_id=job_id,
                status="completed",
                terms_processed=terms_processed,
                terms_added=terms_added,
                terms_updated=terms_updated,
                execution_time_seconds=execution_time,
                started_at=start_time.isoformat(),
                completed_at=end_time.isoformat(),
                error_message=None,
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "run_trending_job",
                    "job_type": job_request.job_type,
                },
            )

            return TrendingJobResponse(
                job_id=job_id if 'job_id' in locals() else "unknown",
                status="failed",
                terms_processed=terms_processed if 'terms_processed' in locals() else 0,
                terms_added=terms_added if 'terms_added' in locals() else 0,
                terms_updated=terms_updated if 'terms_updated' in locals() else 0,
                execution_time_seconds=execution_time if 'execution_time' in locals() else 0.0,
                started_at=start_time.isoformat() if 'start_time' in locals() else datetime.now(timezone.utc).isoformat(),
                completed_at=None,
                error_message=str(e),
            )

    def _generate_sample_trending_terms(self) -> List[dict]:
        """Generate sample trending terms for demonstration."""
        return [
            {
                "term": "no cap",
                "definition": "No lie, for real, I'm telling the truth",
                "category": TrendingCategory.SLANG,
                "popularity_score": 85.5,
                "example_usage": "That movie was fire, no cap!",
                "origin": "Hip hop culture",
                "related_terms": ["fr", "for real", "deadass"],
            },
            {
                "term": "bet",
                "definition": "Okay, sure, I agree",
                "category": TrendingCategory.SLANG,
                "popularity_score": 78.2,
                "example_usage": "Want to grab food later? Bet!",
                "origin": "African American Vernacular English",
                "related_terms": ["okay", "sure", "alright"],
            },
            {
                "term": "periodt",
                "definition": "End of discussion, that's final",
                "category": TrendingCategory.EXPRESSION,
                "popularity_score": 72.8,
                "example_usage": "You're the best, periodt!",
                "origin": "Drag culture, popularized on social media",
                "related_terms": ["period", "end of story", "that's it"],
            },
            {
                "term": "main character",
                "definition": "Someone who thinks they're the protagonist of their own story",
                "category": TrendingCategory.MEME,
                "popularity_score": 69.1,
                "example_usage": "She's really living her main character moment",
                "origin": "Social media/TikTok",
                "related_terms": ["protagonist", "main energy", "main character syndrome"],
            },
            {
                "term": "it's giving",
                "definition": "It's giving off a certain vibe or energy",
                "category": TrendingCategory.EXPRESSION,
                "popularity_score": 81.3,
                "example_usage": "This outfit is giving main character energy",
                "origin": "Drag culture, popularized on social media",
                "related_terms": ["vibes", "energy", "giving off"],
            },
        ]
