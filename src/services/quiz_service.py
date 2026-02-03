from logging import Logger

from bson.objectid import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from domain.models import AnswerType, CardDto


class SubmitAnswerResult:
    """Result of submitting a quiz answer."""

    def __init__(self, correct: bool, correct_answer: str | None = None):
        self.correct = correct
        self.correct_answer = correct_answer


class QuizService:
    """Application service for quiz operations."""

    def __init__(
        self,
        db: AsyncDatabase,
        logger: Logger,
    ):
        self._db = db
        self._logger = logger
        self._collection = db.flashcards

    async def submit_answer(
        self,
        card_id: str,
        answer_type: AnswerType,
        user_answer: str,
    ) -> SubmitAnswerResult:
        """Validate answer and optionally increment use_count. Returns result."""
        try:
            oid = ObjectId(card_id)
        except Exception:
            raise ValueError("Invalid card_id.") from None

        doc = await self._collection.find_one({"_id": oid})
        if doc is None:
            raise LookupError("Card not found.")

        card = CardDto.model_validate(doc)
        user_answer_normalized = user_answer.strip().lower()
        if answer_type == AnswerType.russian:
            correct_answer_normalized = card.russian.strip().lower()
            correct_answer_display = card.russian
        else:
            correct_answer_normalized = card.english.strip().lower()
            correct_answer_display = card.english

        if user_answer_normalized == correct_answer_normalized:
            await self._collection.update_one(
                {"_id": oid},
                {"$inc": {"use_count": 1}},
            )
            self._logger.info("Correct answer for card %s", card_id)
            return SubmitAnswerResult(correct=True, correct_answer=None)
        return SubmitAnswerResult(
            correct=False,
            correct_answer=correct_answer_display,
        )
