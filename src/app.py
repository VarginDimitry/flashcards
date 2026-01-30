import asyncio
from logging import Logger

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from dishka import AsyncContainer, make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from handlers import get_router
from provider import RootProvider


def create_container() -> AsyncContainer:
    return make_async_container(
        AiogramProvider(),
        RootProvider(),
    )


async def setup_logging(container: AsyncContainer) -> None:
    logger = await container.get(Logger)

    from aiogram import loggers as aiogram_loggers

    logger_types = ("dispatcher", "event", "middlewares", "webhook", "scene")
    for logger_type in logger_types:
        setattr(aiogram_loggers, logger_type, logger.getChild(f"aiogram.{logger_type}"))


async def main() -> None:
    container = create_container()
    await setup_logging(container)

    dp = Dispatcher(storage=await container.get(BaseStorage))
    dp.include_routers(get_router())
    setup_dishka(container=container, router=dp, auto_inject=True)

    await dp.start_polling(await container.get(Bot))


if __name__ == "__main__":
    asyncio.run(main())
