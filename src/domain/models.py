from datetime import datetime
from enum import Enum

from bson.objectid import ObjectId
from pydantic import BaseModel, Field


class AnswerType(str, Enum):
    english = "english"
    russian = "russian"


class InsertCardDto(BaseModel):
    """Domain DTO for creating a flash card (persistence layer)."""

    english: str
    russian: str
    image_url: str
    priority: int = 0
    use_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CardDto(InsertCardDto):
    """Domain DTO for a flash card loaded from persistence."""

    id: ObjectId = Field(alias="_id")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        arbitrary_types_allowed = True
