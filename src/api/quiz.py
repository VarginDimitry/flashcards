from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException

from api.schemas import CardResponse, SubmitAnswerRequest, SubmitAnswerResponse
from services import CardService, QuizService

quiz_router = APIRouter('/quiz', route_class=DishkaRoute)

QUIZ_LIMIT = 10


@quiz_router.get("/cards", response_model=list[CardResponse])
async def get_quiz_cards(
    limit: int = QUIZ_LIMIT,
    card_service: FromDishka[CardService] = None,
) -> list[CardResponse]:
    """Get a list of flash cards for a quiz (sorted by priority desc, use_count asc)."""
    try:
        results = await card_service.get_quiz_cards(limit=limit)
        return [
            CardResponse(
                id=r.id,
                english=r.english,
                russian=r.russian,
                image_url=r.image_url,
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching quiz cards.",
        ) from e


@router.post("/answer", response_model=SubmitAnswerResponse)
async def submit_quiz_answer(
    body: SubmitAnswerRequest,
    quiz_service: FromDishka[QuizService] = None,
) -> SubmitAnswerResponse:
    """Submit an answer for a quiz question. Returns whether the answer is correct."""
    try:
        result = await quiz_service.submit_answer(
            card_id=body.card_id,
            answer_type=body.answer_type,
            user_answer=body.user_answer,
        )
        return SubmitAnswerResponse(
            correct=result.correct,
            correct_answer=result.correct_answer,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting the answer.",
        ) from e
