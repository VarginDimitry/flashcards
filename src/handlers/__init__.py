from aiogram import Router

from .add_card import add_card_router
from .quiz import quiz_router
from .start import start_router


def get_router() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(quiz_router)
    router.include_router(add_card_router)
    return router
