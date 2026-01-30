from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.filters import MY_ID

start_router = Router()


@start_router.message(Command("start"), StateFilter("*"), F.from_user.id == MY_ID)
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()

    await message.answer(
        "Hi! 👋\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/quiz - Start quiz\n"
        "/add_card - Add card"
    )
