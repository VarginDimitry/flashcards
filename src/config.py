from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class S3Config(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    url: str
    login: str
    password: str


class MongoConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    url: str
    database: str


class Config(BaseSettings):
    app_name: str = "quizpy"
    mongo: MongoConfig
    s3: S3Config

    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
