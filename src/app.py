import logging
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from api import get_api_router
from config import Config
from provider import RootProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = app.state.dishka_container
    config = await container.get(Config)
    logger = await container.get(logging.Logger)
    logger.info("Starting %s", config.app_name)
    yield
    logger.info("Shutting down %s", config.app_name)
    await container.close()


def create_app() -> FastAPI:
    container = make_async_container(RootProvider())
    app = FastAPI(
        title="QuizPy API",
        description="API for adding flash cards, getting quiz cards, and submitting quiz answers.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(get_api_router())
    setup_dishka(container=container, app=app)
    return app


app = create_app()
