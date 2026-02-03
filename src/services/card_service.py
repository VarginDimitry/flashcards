import uuid
from logging import Logger

from miniopy_async import Minio
from pymongo.asynchronous.database import AsyncDatabase

from domain.models import CardDto, InsertCardDto

BUCKET_NAME = "cards"
PRESIGNED_EXPIRY_SECONDS = 3600


class AddCardResult:
    """Result of adding a card."""

    def __init__(self, id: str, english: str, russian: str, image_url: str):
        self.id = id
        self.english = english
        self.russian = russian
        self.image_url = image_url


class QuizCardResult:
    """A card with presigned image URL for quiz."""

    def __init__(self, id: str, english: str, russian: str, image_url: str):
        self.id = id
        self.english = english
        self.russian = russian
        self.image_url = image_url


class CardService:
    """Application service for card operations."""

    def __init__(
        self,
        db: AsyncDatabase,
        s3: Minio,
        logger: Logger,
    ):
        self._db = db
        self._s3 = s3
        self._logger = logger
        self._collection = db.flashcards

    async def _upload_image(self, content: bytes, content_type: str) -> str:
        if not await self._s3.bucket_exists(BUCKET_NAME):
            await self._s3.make_bucket(BUCKET_NAME)
        object_name = f"api/{uuid.uuid4()}.jpg"
        await self._s3.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=content,
            length=len(content),
            content_type=content_type or "image/jpeg",
        )
        return f"{BUCKET_NAME}/{object_name}"

    async def _get_presigned_url(self, storage_path: str) -> str:
        bucket, object_name = storage_path.split("/", 1)
        return await self._s3.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=PRESIGNED_EXPIRY_SECONDS,
        )

    async def add_card(
        self,
        english: str,
        russian: str,
        image_content: bytes,
        content_type: str,
    ) -> AddCardResult:
        """Upload image to S3, persist card in MongoDB, return result."""
        image_url = await self._upload_image(
            image_content,
            content_type or "image/jpeg",
        )
        self._logger.info("Uploaded image to storage: %s", image_url)

        card = InsertCardDto(
            english=english.strip(),
            russian=russian.strip(),
            image_url=image_url,
        )
        result = await self._collection.insert_one(card.model_dump())
        card_id = str(result.inserted_id)
        self._logger.info("Created flash card with ID: %s", card_id)

        return AddCardResult(
            id=card_id,
            english=card.english,
            russian=card.russian,
            image_url=image_url,
        )

    async def get_quiz_cards(self, limit: int = 10) -> list[QuizCardResult]:
        """Return cards for quiz with presigned image URLs."""
        cursor = (
            self._collection.find()
            .sort([("priority", -1), ("use_count", 1)])
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        result = []
        for doc in docs:
            card = CardDto.model_validate(doc)
            presigned_url = await self._get_presigned_url(card.image_url)
            result.append(
                QuizCardResult(
                    id=str(card.id),
                    english=card.english,
                    russian=card.russian,
                    image_url=presigned_url,
                )
            )
        self._logger.info("Returned %d quiz cards", len(result))
        return result
