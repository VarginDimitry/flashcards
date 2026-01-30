from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

start_router = Router()


@start_router.message(Command("start"), StateFilter("*"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()

    await message.answer(
        "Hi! 👋\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/quiz - Start quiz\n"
        "/add_card - Add card"
    )
