import logging

from aiogram import Bot
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from coloredlogs import ColoredFormatter
from dishka import provide, Provider, Scope
from miniopy_async import Minio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from config import Config


class RootProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_config(self) -> Config:
        return Config()

    @provide(scope=Scope.APP)
    def provide_logger(self, config: Config) -> logging.Logger:
        logger = logging.getLogger(config.app_name)
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            ColoredFormatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        logger.addHandler(console_handler)

        return logger

    @provide(scope=Scope.APP)
    async def provide_bot(self, config: Config) -> Bot:
        bot = Bot(token=config.bot.token)
        if config.bot.refresh_bot_data:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Старт"),
                    BotCommand(command="quiz", description="Начать квиз"),
                    BotCommand(command="add_card", description="Добавить карточку"),
                ]
            )
        return bot

    @provide(scope=Scope.APP)
    def provide_storage(self) -> BaseStorage:
        return MemoryStorage()

    @provide(scope=Scope.APP)
    async def provide_mongo_client(self, config: Config) -> AsyncDatabase:
        client = AsyncMongoClient(config.mongo.url)
        db = client.get_database(config.mongo.database)
        await db.list_collection_names()
        return db

    @provide(scope=Scope.APP)
    def provide_s3(self, config: Config) -> Minio:
        return Minio(
            endpoint=config.s3.url,
            secure=False,
            access_key=config.s3.login,
            secret_key=config.s3.password,
        )
