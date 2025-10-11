"""Service for LLM-based validation of slang submissions using Claude + Tavily web search."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any

from tavily import TavilyClient  # type: ignore

from models.slang import (
    SlangSubmission,
    LLMValidationResult,
    LLMValidationEvidence,
    SlangSubmissionStatus,
)
from models.config import SlangValidationConfig, LLMConfig
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class SlangValidationService:
    """Service for validating slang submissions using Claude + Tavily web search."""

    def __init__(self) -> None:
        """Initialize slang validation service."""
        self.config_service = get_config_service()
        self.validation_config = self.config_service.get_config(SlangValidationConfig)
        self.llm_config = self.config_service.get_config(LLMConfig)
        self.bedrock_client = aws_services.bedrock_client

    @tracer.trace_method("validate_submission")
    def validate_submission(self, submission: SlangSubmission) -> LLMValidationResult:
        """
        Validate a slang submission using Claude + Tavily web search.

        Args:
            submission: The slang submission to validate

        Returns:
            LLMValidationResult with validation details and confidence score

        Raises:
            BusinessLogicError: If validation fails
        """
        logger.log_business_event(
            "slang_validation_started",
            {
                "submission_id": submission.submission_id,
                "slang_term": submission.slang_term,
                "web_search_enabled": self.validation_config.web_search_enabled,
            },
        )

        try:
            # Get web search results if enabled
            search_results = []
            if (
                self.validation_config.web_search_enabled
                and self.validation_config.tavily_api_key
            ):
                search_results = self._web_search(submission.slang_term)

            # Call Claude to validate with search results
            validation_result = self._call_claude(submission, search_results)

            logger.log_business_event(
                "slang_validation_completed",
                {
                    "submission_id": submission.submission_id,
                    "is_valid": validation_result.is_valid,
                    "confidence": float(validation_result.confidence),
                    "usage_score": validation_result.usage_score,
                    "search_results_count": len(search_results),
                },
            )

            return validation_result

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "validate_submission",
                    "submission_id": submission.submission_id,
                },
            )
            # Fall back to conservative validation on error
            return self._fallback_validation(submission)

    def _web_search(self, slang_term: str) -> List[Dict[str, Any]]:
        """
        Search the web for evidence of slang term usage using Tavily SDK.

        Args:
            slang_term: The slang term to search for

        Returns:
            List of search results with content and URLs
        """
        try:
            # Initialize Tavily client
            client = TavilyClient(api_key=self.validation_config.tavily_api_key)

            # Search for the slang term
            response = client.search(
                query=f"{slang_term} gen z slang meaning urban dictionary",
                search_depth="advanced",  # More thorough search
                max_results=self.validation_config.max_search_results,
                include_answer=False,  # We don't need Tavily's LLM answer
                include_raw_content=False,  # Clean snippets only
            )

            results = response.get("results", [])

            logger.log_business_event(
                "web_search_completed",
                {
                    "slang_term": slang_term,
                    "results_count": len(results),
                    "response_time": response.get("response_time", 0),
                },
            )

            return results

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "web_search",
                    "slang_term": slang_term,
                },
            )
            # Return empty results on error - validation will proceed without web evidence
            return []

    def _call_claude(
        self, submission: SlangSubmission, search_results: List[Dict[str, Any]]
    ) -> LLMValidationResult:
        """
        Call Claude to validate slang submission with web search results.

        Args:
            submission: The slang submission to validate
            search_results: Results from Tavily web search

        Returns:
            LLMValidationResult with validation details
        """
        try:
            # Create validation prompt
            prompt = self._create_validation_prompt(submission, search_results)

            # Call Claude via Bedrock
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.llm_config.max_tokens,
                "temperature": self.llm_config.temperature,
                "top_p": self.llm_config.top_p,
            }

            response = self.bedrock_client.invoke_model(
                modelId=self.llm_config.model,
                body=json.dumps(body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            completion_text = response_body["content"][0]["text"]

            # Parse JSON response from Claude
            result = self._parse_llm_response(completion_text, submission)
            return result

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "call_claude",
                    "submission_id": submission.submission_id,
                },
            )
            # Fall back to conservative validation on error
            raise

    def _create_validation_prompt(
        self, submission: SlangSubmission, search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Create validation prompt for Claude with web search results.

        Args:
            submission: The slang submission
            search_results: Web search results from Tavily

        Returns:
            Formatted prompt string
        """
        # Format search results for the prompt
        web_evidence = ""
        if search_results:
            web_evidence = "\n\nWEB SEARCH RESULTS:\n"
            for i, result in enumerate(search_results, 1):
                web_evidence += f"\n{i}. {result.get('title', 'Unknown')}\n"
                web_evidence += f"   URL: {result.get('url', 'N/A')}\n"
                web_evidence += f"   Content: {result.get('content', 'N/A')[:300]}...\n"
        else:
            web_evidence = "\n\nWEB SEARCH RESULTS: No results available (proceeding without web evidence)\n"

        prompt = f"""You are a Gen Z slang validator. Analyze this submission and the web evidence provided.

SUBMISSION:
Term: {submission.slang_term}
Definition: {submission.meaning}
Example: {submission.example_usage or 'Not provided'}
{web_evidence}

ANALYSIS TASKS:
1. Is this real Gen Z slang currently in use?
2. Is the submitted definition accurate based on web evidence?
3. How widespread is the usage? (scale 1-10, where 10 = extremely common like "rizz", 1 = unknown/made up)
4. What evidence supports your conclusion?

RETURN FORMAT (JSON ONLY):
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "evidence": [{{"source": "url or description", "example": "relevant quote or finding"}}],
  "recommended_definition": "corrected definition if user's is inaccurate, otherwise null",
  "usage_score": 1-10
}}

GUIDELINES:
- High confidence (>0.85) only if you find strong web evidence from multiple sources
- Usage score 7-10 requires evidence from Urban Dictionary, social media, or news sources
- If web results are empty or inconclusive, use lower confidence (0.3-0.6)
- Be honest about lack of evidence - don't make assumptions

Return ONLY the JSON object, no other text."""
        return prompt

    def _parse_llm_response(
        self, response_text: str, submission: SlangSubmission
    ) -> LLMValidationResult:
        """
        Parse Claude's JSON response into validation result.

        Args:
            response_text: Raw response from Claude
            submission: Original submission

        Returns:
            Parsed LLMValidationResult
        """
        try:
            # Extract JSON from response (may be wrapped in markdown or text)
            cleaned_response = response_text.strip()

            # Handle markdown code blocks
            if "```json" in cleaned_response:
                start = cleaned_response.find("```json") + 7
                end = cleaned_response.find("```", start)
                cleaned_response = cleaned_response[start:end].strip()
            elif "```" in cleaned_response:
                start = cleaned_response.find("```") + 3
                end = cleaned_response.find("```", start)
                cleaned_response = cleaned_response[start:end].strip()

            data = json.loads(cleaned_response)

            # Parse evidence
            evidence_list = []
            for ev in data.get("evidence", []):
                evidence_list.append(
                    LLMValidationEvidence(
                        source=ev.get("source", "unknown"),
                        example=ev.get("example", ""),
                    )
                )

            return LLMValidationResult(
                is_valid=data.get("is_valid", False),
                confidence=Decimal(str(data.get("confidence", 0.5))),
                evidence=evidence_list,
                recommended_definition=data.get("recommended_definition"),
                usage_score=data.get("usage_score", 5),
                validated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "parse_agent_response",
                    "submission_id": submission.submission_id,
                    "response_preview": response_text[:200],
                },
            )
            # Return conservative result if parsing fails
            return self._fallback_validation(submission)

    def _fallback_validation(self, submission: SlangSubmission) -> LLMValidationResult:
        """
        Provide conservative validation when agent is unavailable.

        Args:
            submission: The slang submission

        Returns:
            Conservative LLMValidationResult (requires manual review)
        """
        logger.log_business_event(
            "slang_validation_fallback",
            {"submission_id": submission.submission_id},
        )

        return LLMValidationResult(
            is_valid=True,  # Assume valid, but require manual review
            confidence=Decimal("0.5"),  # Medium confidence - requires review
            evidence=[
                LLMValidationEvidence(
                    source="fallback",
                    example="Validation agent unavailable - manual review required",
                )
            ],
            recommended_definition=None,
            usage_score=5,  # Neutral score
            validated_at=datetime.now(timezone.utc),
        )

    def should_auto_approve(self, validation_result: LLMValidationResult) -> bool:
        """
        Determine if submission should be auto-approved based on confidence.

        Args:
            validation_result: The validation result

        Returns:
            True if should auto-approve, False otherwise
        """
        if not self.validation_config.auto_approval_enabled:
            return False

        threshold = Decimal(str(self.validation_config.auto_approval_threshold))

        return (
            validation_result.is_valid
            and validation_result.confidence >= threshold
            and validation_result.usage_score >= 7  # High usage score
        )

    def determine_status(
        self, validation_result: LLMValidationResult
    ) -> SlangSubmissionStatus:
        """
        Determine submission status based on validation result.

        Args:
            validation_result: The validation result

        Returns:
            Appropriate SlangSubmissionStatus
        """
        if self.should_auto_approve(validation_result):
            return SlangSubmissionStatus.AUTO_APPROVED

        if not validation_result.is_valid:
            return SlangSubmissionStatus.REJECTED

        # Valid but not confident enough for auto-approval
        # Make available for community voting
        return SlangSubmissionStatus.VALIDATED
