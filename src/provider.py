import logging

from coloredlogs import ColoredFormatter
from dishka import provide, Provider, Scope
from miniopy_async import Minio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from config import Config
from services import CardService, QuizService


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

    @provide(scope=Scope.APP)
    def provide_card_service(
        self,
        db: AsyncDatabase,
        s3: Minio,
        logger: logging.Logger,
    ) -> CardService:
        return CardService(db, s3, logger)

    @provide(scope=Scope.APP)
    def provide_quiz_service(
        self,
        db: AsyncDatabase,
        logger: logging.Logger,
    ) -> QuizService:
        return QuizService(db, logger)
