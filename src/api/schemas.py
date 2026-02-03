"""Request/response schemas for the API layer."""

from domain.models import AnswerType
from pydantic import BaseModel


class CardResponse(BaseModel):
    id: str
    english: str
    russian: str
    image_url: str


class AddCardResponse(BaseModel):
    id: str
    english: str
    russian: str
    image_url: str


class SubmitAnswerRequest(BaseModel):
    card_id: str
    answer_type: AnswerType
    user_answer: str


class SubmitAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str | None = None
