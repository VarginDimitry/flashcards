import uuid
from logging import Logger
from typing import Any, AsyncIterator

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize
from dishka import FromDishka
from miniopy_async import Minio
from pymongo.asynchronous.database import AsyncDatabase

from models import InsertCardDto

add_card_router = Router()


@add_card_router.message(F.photo, Command("add_card"), StateFilter("*"))
async def add_card_handler(
    message: Message,
    state: FSMContext,
    s3: FromDishka[Minio],
    db: FromDishka[AsyncDatabase],
    logger: FromDishka[Logger],
) -> Any:
    await state.clear()

    error_text = (
        "Please send a message with photo and text in format:\n"
        "/add_card\n"
        "english text\n"
        "russian text"
    )
    if not message.caption or not message.photo:
        return await message.answer(error_text)

    lines = message.caption.strip().split("\n")
    if len(lines) != 3:
        return await message.answer(error_text)

    english = lines[1].strip()
    russian = lines[2].strip()
    if not english or not russian:
        return await message.answer("Both English and Russian text must be non-empty.")

    try:
        image_url = await upload_photo_to_s3(message, s3, logger)
        flash_card = InsertCardDto(
            english=english,
            russian=russian,
            image_url=image_url,
        )

        result = await db.flashcards.insert_one(flash_card.model_dump())
        logger.info(f"Created flash card with ID: {result.inserted_id}")

        await message.answer(
            f"✅ Flash card created successfully!\n\n"
            f"English: {flash_card.english}\n"
            f"Russian: {flash_card.russian}\n"
            f"Image uploaded: {image_url}"
        )

    except Exception as e:
        logger.error(f"Error creating flash card: {e}", exc_info=True)
        await message.answer(
            "An error occurred while creating the flash card. Please try again."
        )


async def upload_photo_to_s3(
    message: Message,
    s3: FromDishka[Minio],
    logger: FromDishka[Logger],
) -> str:
    photo: PhotoSize = message.photo[-1]

    bucket_name = "cards"
    if not await s3.bucket_exists(bucket_name):
        s3.make_bucket(bucket_name)
        logger.info(f"Created bucket: {bucket_name}")

    filename = f"user_{message.from_user.id}/{uuid.uuid4()}.jpg"

    # try:
    #     stream, close_stream = await get_file_stream(message.bot, photo)
    #     await s3.put_object(
    #         bucket_name=bucket_name,
    #         object_name=filename,
    #         data=stream,
    #         length=-1,
    #         content_type="image/jpeg",
    #     )
    # finally:
    #     if close_stream:
    #         await stream.aclose()

    file = await message.bot.download(photo.file_id)
    await s3.put_object(
        bucket_name=bucket_name,
        object_name=filename,
        data=file,
        length=-1,
        part_size=2**20 * 8,
        content_type="image/jpeg",
    )

    image_url = f"{bucket_name}/{filename}"
    logger.info(f"Uploaded image to S3: {image_url}")
    return image_url


# cant send stream to s3
async def get_file_stream(
    bot: Bot,
    photo: PhotoSize,
    chunk_size: int = 65536,
    timeout: int = 30,
) -> tuple[AsyncIterator[bytes], bool]:
    file = await bot.get_file(photo.file_id)

    close_stream = False
    if bot.session.api.is_local:
        stream = bot.__aiofiles_reader(
            bot.session.api.wrap_local_file.to_local(file.file_path),
            chunk_size=chunk_size,
        )
        close_stream = True
    else:
        url = bot.session.api.file_url(bot.token, file.file_path)
        stream = bot.session.stream_content(
            url=url,
            timeout=timeout,
            chunk_size=chunk_size,
            raise_for_status=True,
        )

    return stream, close_stream
