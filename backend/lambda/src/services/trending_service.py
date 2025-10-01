"""Trending service for trending terms business logic."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from models.trending import (
    TrendingTerm,
    TrendingCategory,
    TrendingListResponse,
    TrendingJobRequest,
    TrendingJobResponse,
)
from models.users import UserTier
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service
from models.config import LLMConfig
from utils.exceptions import ValidationError
from repositories.trending_repository import TrendingRepository
from services.user_service import UserService


class TrendingService:
    """Service for trending terms business logic."""

    def __init__(self) -> None:
        """Initialize trending service."""
        self.repository = TrendingRepository()
        self.config_service = get_config_service()
        self.bedrock_client = aws_services.bedrock_client
        self.llm_config = self.config_service.get_config(LLMConfig)
        self.user_service = UserService()

    @tracer.trace_method("get_trending_terms")
    def get_trending_terms(
        self,
        user_id: str,
        limit: int = 50,
        category: Optional[TrendingCategory] = None,
        active_only: bool = True,
    ) -> TrendingListResponse:
        """Get trending terms with optional filtering and tier-based features."""
        try:
            # Get user tier for premium features
            # Default to FREE tier (most restrictive) for safety
            user_tier = UserTier.FREE
            user = self.user_service.get_user(user_id)
            if user:
                user_tier = user.tier
                logger.log_business_event(
                    "trending_user_tier_determined",
                    {"user_id": user_id, "tier": user_tier},
                )
            else:
                # User not found or error - default to FREE tier for security
                logger.log_business_event(
                    "trending_user_not_found_defaulting_to_free",
                    {"user_id": user_id, "reason": "user_not_found_or_error"},
                )

            # Apply tier-based limits
            if user_tier == UserTier.FREE:
                # Free users get limited access
                if limit > 10:
                    limit = 10
                # Free users can only access 'slang' category
                if category and category != TrendingCategory.SLANG:
                    raise ValidationError(
                        "Category filtering is a premium feature. Free users can only access 'slang' category."
                    )
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
                last_updated=datetime.now(timezone.utc),
                category_filter=category,
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_trending_terms",
                    "limit": limit,
                    "category": category if category else None,
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
        popularity_score: Decimal = Decimal("0.0"),
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
                    "category": category,
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
        popularity_score: Optional[Decimal] = None,
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
                existing_term.example_usage = (
                    example_usage.strip() if example_usage else None
                )

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
                    "category": existing_term.category,
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

            # Generate trending data using Bedrock AI
            if job_request.job_type == "gen_z_slang_analysis":
                # Use Bedrock to generate trending Gen Z slang terms
                ai_generated_terms = self._generate_trending_terms_with_bedrock()

                for term_data in ai_generated_terms:
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
                execution_time_seconds=Decimal(str(execution_time)),
                started_at=start_time,
                completed_at=end_time,
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
                job_id=job_id if "job_id" in locals() else "unknown",
                status="failed",
                terms_processed=terms_processed if "terms_processed" in locals() else 0,
                terms_added=terms_added if "terms_added" in locals() else 0,
                terms_updated=terms_updated if "terms_updated" in locals() else 0,
                execution_time_seconds=(
                    Decimal(str(execution_time))
                    if "execution_time" in locals()
                    else Decimal("0.0")
                ),
                started_at=(
                    start_time
                    if "start_time" in locals()
                    else datetime.now(timezone.utc)
                ),
                completed_at=None,
                error_message=str(e),
            )

    @tracer.trace_method("generate_trending_terms_with_bedrock")
    def _generate_trending_terms_with_bedrock(self) -> List[dict]:
        """Generate trending Gen Z slang terms using Bedrock AI."""
        try:
            # Create a comprehensive prompt for Bedrock
            prompt = self._create_trending_terms_prompt()

            # Call Bedrock to generate trending terms
            response = self._call_bedrock_for_trending_terms(prompt)

            # Parse the response into trending terms
            trending_terms = self._parse_bedrock_trending_response(response)

            logger.log_business_event(
                "bedrock_trending_generation",
                {
                    "terms_generated": len(trending_terms),
                    "model_used": self.llm_config.model,
                },
            )

            return trending_terms

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "generate_trending_terms_with_bedrock"},
            )
            # Fallback to sample terms if Bedrock fails
            return self._generate_fallback_trending_terms()

    def _create_trending_terms_prompt(self) -> str:
        """Create a prompt for Bedrock to generate trending Gen Z slang terms."""
        return """You are a Gen Z slang expert and cultural analyst. Generate a list of currently trending Gen Z slang terms, expressions, and phrases that are popular in 2024.

For each term, provide:
1. The slang term or phrase
2. A clear, accurate definition
3. The category (slang, meme, expression, hashtag, or phrase)
4. A popularity score from 0-100 based on current usage
5. A realistic example of how it's used in context
6. The origin or cultural background
7. Related terms or synonyms

Focus on terms that are:
- Currently popular among Gen Z (ages 13-26)
- Used on social media platforms like TikTok, Instagram, Twitter
- Recent or trending in 2024
- Authentic and not outdated

Return the response as a JSON array with this exact structure:
[
  {
    "term": "example term",
    "definition": "clear definition",
    "category": "slang|meme|expression|hashtag|phrase",
    "popularity_score": 85.5,
    "example_usage": "realistic example sentence",
    "origin": "cultural background or source",
    "related_terms": ["related", "synonyms", "variations"]
  }
]

Generate 15-20 diverse trending terms across different categories. Make sure the JSON is valid and properly formatted."""

    @tracer.trace_method("call_bedrock_for_trending_terms")
    def _call_bedrock_for_trending_terms(self, prompt: str) -> str:
        """Call Bedrock to generate trending terms."""
        try:
            # Prepare the request body for Claude 3 Haiku
            request_body = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "anthropic_version": "bedrock-2023-05-31",
            }

            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.llm_config.model,
                body=json.dumps(request_body),
                contentType="application/json",
            )

            # Parse the response
            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"]

            return content

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "call_bedrock_for_trending_terms",
                    "model": self.llm_config.model,
                },
            )
            raise

    def _parse_bedrock_trending_response(self, response: str) -> List[dict]:
        """Parse Bedrock response into trending terms list."""
        try:
            # Extract JSON from the response (handle markdown formatting)
            json_start = response.find("[")
            json_end = response.rfind("]") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON array found in response")

            json_str = response[json_start:json_end]
            trending_data = json.loads(json_str)

            # Validate and clean the data
            validated_terms = []
            for term_data in trending_data:
                if self._validate_trending_term_data(term_data):
                    # Ensure category is valid
                    try:
                        category = TrendingCategory(term_data["category"].lower())
                    except ValueError:
                        category = TrendingCategory.SLANG  # Default fallback

                    validated_terms.append(
                        {
                            "term": term_data["term"].strip(),
                            "definition": term_data["definition"].strip(),
                            "category": category,
                            "popularity_score": Decimal(
                                str(term_data["popularity_score"])
                            ),
                            "example_usage": term_data.get("example_usage", "").strip(),
                            "origin": term_data.get("origin", "").strip(),
                            "related_terms": term_data.get("related_terms", []),
                        }
                    )

            return validated_terms

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "parse_bedrock_trending_response",
                    "response_preview": response[:200] if response else "None",
                },
            )
            # Return fallback terms if parsing fails
            return self._generate_fallback_trending_terms()

    def _validate_trending_term_data(self, term_data: dict) -> bool:
        """Validate that trending term data has required fields."""
        required_fields = ["term", "definition", "category", "popularity_score"]
        return all(field in term_data for field in required_fields)

    def _generate_fallback_trending_terms(self) -> List[dict]:
        """Generate fallback trending terms if Bedrock fails."""
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
                "related_terms": [
                    "protagonist",
                    "main energy",
                    "main character syndrome",
                ],
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
