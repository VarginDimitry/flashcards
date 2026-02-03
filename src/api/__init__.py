from fastapi import APIRouter

from api.cards import card_router
from api.quiz import quiz_router


def get_api_router() -> APIRouter:
    router = APIRouter('/api')
    router.include_router(card_router)
    router.include_router(quiz_router)
    return router
