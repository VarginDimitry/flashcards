from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.schemas import AddCardResponse
from services import CardService

card_router = APIRouter('/cards', route_class=DishkaRoute)


@card_router.post("/add", response_model=AddCardResponse, status_code=201)
async def add_card(
    card_service: FromDishka[CardService],
    english: str = Form(),
    russian: str = Form(),
    image: UploadFile = File(),
) -> AddCardResponse:
    """Add a new flash card with English text, Russian text, and an image."""
    if not english.strip() or not russian.strip():
        raise HTTPException(
            status_code=400,
            detail="Both english and russian must be non-empty.",
        )
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (e.g. image/jpeg, image/png).",
        )

    try:
        content = await image.read()
        result = await card_service.add_card(
            english=english,
            russian=russian,
            image_content=content,
            content_type=image.content_type,
        )
        return AddCardResponse(
            id=result.id,
            english=result.english,
            russian=result.russian,
            image_url=result.image_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating the flash card.",
        ) from e
