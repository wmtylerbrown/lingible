"""Repository for canonical lexicon terms (LexiconTable)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from models.base import LingibleBaseModel
from models.quiz import QuizCategory, QuizDifficulty
from models.slang import ApprovalStatus, SlangTerm
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.smart_logger import logger
from utils.tracing import tracer


class LexiconRepository:
    """Manage canonical slang lexicon records."""

    def __init__(self) -> None:
        config_service = get_config_service()
        self.table_name = config_service._get_env_var("LEXICON_TABLE")
        self.table = aws_services.get_table(self.table_name)

    @staticmethod
    def _term_pk(term: str) -> str:
        return f"TERM#{term.lower()}"

    @staticmethod
    def _lexicon_sk() -> str:
        return "METADATA#lexicon"

    def save_lexicon_term(self, term: SlangTerm) -> bool:
        """Create or update a lexicon entry."""
        try:
            item = self._term_to_item(term)
            self.table.put_item(Item=item)
            return True
        except Exception as exc:
            logger.log_error(exc, {"operation": "save_lexicon_term", "term": term.term})
            return False

    # Backwards compatibility for scripts/tests
    create_lexicon_term = save_lexicon_term

    def _term_to_item(self, term: SlangTerm) -> Dict[str, Any]:
        quiz_score = self._derive_quiz_score(term)
        created_at_value = getattr(term, "created_at", None)
        if created_at_value and hasattr(created_at_value, "isoformat"):
            created_at = created_at_value.isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()
        item: Dict[str, Any] = {
            "PK": self._term_pk(term.term),
            "SK": self._lexicon_sk(),
            "term": term.term,
            "gloss": term.gloss,
            "meaning": term.gloss,
            "examples": term.examples,
            "tags": term.tags,
            "status": term.status.value,
            "confidence": LingibleBaseModel._to_dynamodb_value(term.confidence),
            "regions": term.regions,
            "momentum": LingibleBaseModel._to_dynamodb_value(term.momentum),
            "sources": term.sources,
            "first_attested": term.first_attested,
            "first_attested_confidence": term.first_attested_confidence,
            "attestation_note": term.attestation_note,
            "is_quiz_eligible": term.is_quiz_eligible,
            "quiz_category": term.quiz_category.value,
            "quiz_difficulty": term.quiz_difficulty.value,
            "quiz_score": LingibleBaseModel._to_dynamodb_value(quiz_score),
            "times_in_quiz": term.times_in_quiz or 0,
            "quiz_accuracy_rate": LingibleBaseModel._to_dynamodb_value(
                term.quiz_accuracy_rate or 0.5
            ),
            "source": "SOURCE#lexicon",
            "created_at": created_at,
        }
        if term.example_usage:
            item["example_usage"] = term.example_usage
        return item

    def _derive_quiz_score(self, term: SlangTerm) -> float:
        # Higher score for newer/more confident terms
        confidence = float(term.confidence or 0.8)
        momentum = float(term.momentum or 1.0)
        return round(confidence * momentum, 4)

    def _item_to_slang_term(self, item: Dict[str, Any]) -> Optional[SlangTerm]:
        try:
            return SlangTerm(
                term=item.get("term", ""),
                gloss=item.get("gloss", item.get("meaning", "")),
                examples=item.get("examples", []),
                tags=item.get("tags", []),
                status=ApprovalStatus(item.get("status", ApprovalStatus.APPROVED)),
                confidence=float(item.get("confidence", 0.8)),
                regions=item.get("regions", []),
                momentum=float(item.get("momentum", 1.0)),
                sources=item.get("sources", {}),
                first_attested=item.get("first_attested"),
                first_attested_confidence=item.get("first_attested_confidence"),
                attestation_note=item.get("attestation_note"),
                is_quiz_eligible=bool(item.get("is_quiz_eligible", False)),
                quiz_category=QuizCategory(
                    item.get("quiz_category", QuizCategory.GENERAL.value)
                ),
                quiz_difficulty=QuizDifficulty(
                    item.get("quiz_difficulty", QuizDifficulty.BEGINNER.value)
                ),
                quiz_accuracy_rate=(
                    float(item.get("quiz_accuracy_rate", 0.5))
                    if item.get("quiz_accuracy_rate") is not None
                    else None
                ),
                times_in_quiz=(
                    int(item.get("times_in_quiz", 0))
                    if item.get("times_in_quiz") is not None
                    else None
                ),
            )
        except Exception as exc:
            logger.log_error(
                exc, {"operation": "_item_to_slang_term", "term": item.get("term")}
            )
            return None

    @tracer.trace_database_operation("query", "lexicon")
    def get_all_lexicon_terms(self) -> List[SlangTerm]:
        try:
            response = self.table.query(
                IndexName="LexiconSourceIndex",
                KeyConditionExpression="source = :source",
                ExpressionAttributeValues={":source": "SOURCE#lexicon"},
            )
            return self._convert_items(response.get("Items", []))
        except Exception as exc:
            logger.log_error(exc, {"operation": "get_all_lexicon_terms"})
            return []

    def _convert_items(self, items: List[Dict[str, Any]]) -> List[SlangTerm]:
        terms: List[SlangTerm] = []
        for item in items:
            term = self._item_to_slang_term(item)
            if term:
                terms.append(term)
        return terms

    @tracer.trace_database_operation("get", "lexicon")
    def get_term_by_slang(self, slang_term: str) -> Optional[SlangTerm]:
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                ExpressionAttributeValues={
                    ":pk": self._term_pk(slang_term),
                    ":sk": "METADATA",
                },
                Limit=1,
            )
            items = response.get("Items", [])
            if not items:
                return None
            return self._item_to_slang_term(items[0])
        except Exception as exc:
            logger.log_error(
                exc,
                {"operation": "get_term_by_slang", "slang_term": slang_term},
            )
            return None

    @tracer.trace_database_operation("scan", "lexicon")
    def get_all_approved_terms(self) -> List[SlangTerm]:
        try:
            response = self.table.scan(
                FilterExpression="#status = :approved",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":approved": ApprovalStatus.APPROVED.value},
            )
            return self._convert_items(response.get("Items", []))
        except Exception as exc:
            logger.log_error(exc, {"operation": "get_all_approved_terms"})
            return []

    def mark_exported(self, term: str, source: str) -> None:
        try:
            self.table.update_item(
                Key={"PK": self._term_pk(term), "SK": self._lexicon_sk()},
                UpdateExpression="SET last_exported_source = :source, last_exported_at = :timestamp",
                ExpressionAttributeValues={
                    ":source": source,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as exc:
            logger.log_error(
                exc,
                {"operation": "mark_exported", "term": term, "source": source},
            )

    @tracer.trace_database_operation("query", "lexicon_difficulty")
    def get_quiz_eligible_terms(
        self,
        difficulty: QuizDifficulty,
        limit: int = 10,
        exclude_terms: List[str] | None = None,
    ) -> List[SlangTerm]:
        try:
            response = self.table.query(
                IndexName="LexiconQuizDifficultyIndex",
                KeyConditionExpression="quiz_difficulty = :difficulty",
                ExpressionAttributeValues={":difficulty": difficulty.value},
                Limit=limit * 2,
                ScanIndexForward=False,
            )
            excluded = set(exclude_terms or [])
            items = [
                item
                for item in response.get("Items", [])
                if item.get("is_quiz_eligible") and item.get("term") not in excluded
            ]
            terms: List[SlangTerm] = []
            for item in items:
                term_model = self._item_to_slang_term(item)
                if term_model:
                    terms.append(term_model)
                if len(terms) >= limit:
                    break
            return terms
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "get_quiz_eligible_terms",
                    "difficulty": difficulty.value,
                },
            )
            return []

    @tracer.trace_database_operation("query", "lexicon_category")
    def get_terms_by_category(
        self, category: QuizCategory | str, limit: int = 50
    ) -> List[SlangTerm]:
        try:
            category_value = (
                category.value if isinstance(category, QuizCategory) else str(category)
            )
            response = self.table.query(
                IndexName="LexiconQuizCategoryIndex",
                KeyConditionExpression="quiz_category = :category",
                ExpressionAttributeValues={":category": category_value},
                Limit=limit,
            )
            return self._convert_items(response.get("Items", []))
        except Exception as exc:
            logger.log_error(
                exc,
                {"operation": "get_terms_by_category", "category": category},
            )
            return []

    @tracer.trace_database_operation("update", "lexicon_quiz_stats")
    def update_quiz_statistics(self, term: str, is_correct: bool) -> None:
        try:
            key = {"PK": self._term_pk(term), "SK": self._lexicon_sk()}
            response = self.table.get_item(Key=key)
            item = response.get("Item")
            if not item:
                return

            current_times = int(item.get("times_in_quiz", 0))
            current_accuracy_raw = item.get("quiz_accuracy_rate", Decimal("0.5"))
            # Convert from DynamoDB Decimal to float for calculation
            current_accuracy = (
                float(current_accuracy_raw)
                if isinstance(current_accuracy_raw, Decimal)
                else float(current_accuracy_raw)
            )

            new_times = current_times + 1
            if current_times == 0:
                new_accuracy = LingibleBaseModel._to_dynamodb_value(
                    1.0 if is_correct else 0.0
                )
            else:
                total_correct = current_accuracy * current_times
                if is_correct:
                    total_correct += 1
                new_accuracy = LingibleBaseModel._to_dynamodb_value(
                    total_correct / new_times
                )

            self.table.update_item(
                Key=key,
                UpdateExpression="SET times_in_quiz = :times, quiz_accuracy_rate = :accuracy, last_used_at = :timestamp",
                ExpressionAttributeValues={
                    ":times": new_times,
                    ":accuracy": new_accuracy,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "update_quiz_statistics",
                    "term": term,
                    "is_correct": is_correct,
                },
            )

    def _decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value or "0"))

    @tracer.trace_database_operation("get", "wrong_answer_pool")
    def get_wrong_answer_pool(self, category: str) -> Optional[List[str]]:
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"QUIZPOOL#{category}",
                    "SK": f"CATEGORY#{category}",
                }
            )
            item = response.get("Item")
            return item.get("pool") if item else None
        except Exception as exc:
            logger.log_error(
                exc, {"operation": "get_wrong_answer_pool", "category": category}
            )
            return None

    @tracer.trace_database_operation("create", "wrong_answer_pool")
    def create_wrong_answer_pool(self, category: str, pool: List[str]) -> bool:
        try:
            item = {
                "PK": f"QUIZPOOL#{category}",
                "SK": f"CATEGORY#{category}",
                "category": category,
                "pool": pool,
                "pool_size": len(pool),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.table.put_item(Item=item)
            return True
        except Exception as exc:
            logger.log_error(
                exc,
                {"operation": "create_wrong_answer_pool", "category": category},
            )
            return False
