import random
from enum import Enum
from logging import Logger
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, URLInputFile
from dishka import FromDishka
from miniopy_async import Minio
from pymongo.asynchronous.database import AsyncDatabase

from handlers.filters import MY_ID
from models import CardDto

quiz_router = Router()


class QuizAction(str, Enum):
    IMAGE = "image"
    ENGLISH = "english"
    RUSSIAN = "russian"


class QuizState(StatesGroup):
    answering = State()


def get_random_quiz_actions(card: CardDto) -> tuple[QuizAction, QuizAction]:
    actions = [QuizAction.ENGLISH, QuizAction.RUSSIAN]
    if card.image_url:
        actions.append(QuizAction.IMAGE)

    question_type = random.choice(actions)
    if question_type == QuizAction.IMAGE or question_type == QuizAction.RUSSIAN:
        return question_type, QuizAction.ENGLISH
    elif question_type == QuizAction.ENGLISH:
        return question_type, QuizAction.RUSSIAN
    else:
        raise ValueError(f"Invalid question type: {question_type}")


async def send_question(
    message: Message,
    card: CardDto,
    question_type: QuizAction,
    answer_type: QuizAction,
    current: int,
    total: int,
    s3: Minio,
) -> None:
    if question_type == QuizAction.IMAGE:
        s3_url = await s3.get_presigned_url("GET", *card.image_url.split("/", 1))

        question_text = f"📚 Question {current}/{total}:\n🖼️ [Image shown above]\n\n"
        if answer_type == QuizAction.ENGLISH:
            question_text += "What is the English translation?"
        else:  # RUSSIAN
            question_text += "What is the Russian translation?"

        await message.answer_photo(
            photo=URLInputFile(s3_url),
            caption=question_text,
        )
    elif question_type == QuizAction.ENGLISH:
        question_text = (
            f"📚 Question {current}/{total}:\n"
            f"🇬🇧 English: {card.english}\n\n"
            "What is the Russian translation?"
        )
        await message.answer(question_text)
    else:  # RUSSIAN
        question_text = (
            f"📚 Question {current}/{total}:\n"
            f"🇷🇺 Russian: {card.russian}\n\n"
            "What is the English translation?"
        )
        await message.answer(question_text)


@quiz_router.message(Command("quiz"), StateFilter("*"), F.from_user.id == MY_ID)
async def start_quiz_handler(
    message: Message,
    state: FSMContext,
    db: FromDishka[AsyncDatabase],
    s3: FromDishka[Minio],
    logger: FromDishka[Logger],
) -> Any:
    await state.clear()

    try:
        flashcards_data = (
            await db.flashcards.find()
            .sort([("priority", -1), ("use_count", 1)])
            .limit(10)
            .to_list()
        )
        if not flashcards_data:
            return await message.answer(
                "No flashcards available. Add some cards first using /add_card"
            )
        flashcards = [CardDto.model_validate(card) for card in flashcards_data]

        first_card = flashcards[0]

        question_type, answer_type = get_random_quiz_actions(first_card)

        await state.update_data(
            flashcards=flashcards,
            current_index=0,
            correct_count=0,
            question_type=question_type.value,
            answer_type=answer_type.value,
        )

        # Set state to answering
        await state.set_state(QuizState.answering)

        # Show quiz start message
        await message.answer(f"📚 Quiz started! Total cards: {len(flashcards)}")

        # Show first question based on question type
        await send_question(
            message,
            first_card,
            question_type,
            answer_type,
            1,
            len(flashcards),
            s3,
        )

        logger.info(
            f"Started quiz for user {message.from_user.id} with {len(flashcards)} cards"
        )

    except Exception as e:
        logger.error(f"Error starting quiz: {e}", exc_info=True)
        await message.answer(
            "An error occurred while starting the quiz. Please try again."
        )


@quiz_router.message(QuizState.answering, F.text, F.from_user.id == MY_ID)
async def answer_quiz_handler(
    message: Message,
    state: FSMContext,
    db: FromDishka[AsyncDatabase],
    s3: FromDishka[Minio],
    logger: FromDishka[Logger],
) -> Any:
    """Handle quiz answers, validate them, and move to next question or show error."""
    try:
        # Get current quiz data from state
        data = await state.get_data()
        flashcards_data: list[CardDto] = data.get("flashcards")
        current_index = data.get("current_index")
        correct_count = data.get("correct_count")
        question_type_str = data.get("question_type")
        answer_type_str = data.get("answer_type")

        if (
            flashcards_data is None
            or current_index is None
            or correct_count is None
            or question_type_str is None
            or answer_type_str is None
        ):
            await state.clear()
            return await message.answer(
                "Quiz session expired. Please start again with /quiz"
            )

        # Get current flashcard and action types
        current_card = flashcards_data[current_index]
        question_type = QuizAction(question_type_str)
        answer_type = QuizAction(answer_type_str)

        # Check if answer is correct based on answer type (case-insensitive comparison)
        user_answer = message.text.strip().lower()
        if answer_type == QuizAction.RUSSIAN:
            correct_answer = current_card.russian.strip().lower()
        else:  # ENGLISH
            correct_answer = current_card.english.strip().lower()

        if user_answer == correct_answer:
            # Correct answer - move to next card
            correct_count += 1
            current_index += 1

            # Increment use_count for the card
            await db.flashcards.update_one(
                {"_id": current_card.id},
                {"$inc": {"use_count": 1}},
            )

            # Check if quiz is finished
            if current_index >= len(flashcards_data):
                # Quiz completed
                await state.clear()
                return await message.answer(
                    f"🎉 Quiz completed!\n\n"
                    f"✅ Correct answers: {correct_count}/{len(flashcards_data)}\n"
                    f"📊 Score: {correct_count / len(flashcards_data) * 100:.1f}%\n\n"
                    f"Great job! Start a new quiz with /quiz"
                )

            next_card = flashcards_data[current_index]
            # Get random question and answer types for next question
            next_question_type, next_answer_type = get_random_quiz_actions(next_card)

            # Update state with new index, correct count, and question/answer types
            await state.update_data(
                current_index=current_index,
                correct_count=correct_count,
                question_type=next_question_type.value,
                answer_type=next_answer_type.value,
            )

            # Show success message
            await message.answer("✅ Correct!")

            # Show next question
            await send_question(
                message,
                next_card,
                next_question_type,
                next_answer_type,
                current_index + 1,
                len(flashcards_data),
                s3,
            )

            logger.info(
                f"User {message.from_user.id} answered correctly. "
                f"Progress: {current_index}/{len(flashcards_data)}"
            )
        else:
            # Wrong answer - show error and stay on current question (don't change state)
            await message.answer(
                f"❌ Wrong answer!\n\nYour answer: {message.text}\nPlease try again."
            )

            # Re-show the current question
            await send_question(
                message,
                current_card,
                question_type,
                answer_type,
                current_index + 1,
                len(flashcards_data),
                s3,
            )

            logger.info(
                f"User {message.from_user.id} answered incorrectly. "
                f"Expected: {correct_answer}, Got: {user_answer}"
            )

    except Exception as e:
        logger.error(f"Error handling quiz answer: {e}", exc_info=True)
        await message.answer(
            "An error occurred. Please try again or restart the quiz with /quiz"
        )
