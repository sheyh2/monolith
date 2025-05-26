from pydantic.v1 import Extra
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DB_CONNECTION: str
    DB_HOST: str
    DB_PORT: str
    DB_DATABASE: str
    DB_USERNAME: str
    DB_PASSWORD: str

    class Config:
        env_file = '.env'
        extra = Extra.ignore


def absolute_path(path: str) -> str:
    return str(Path(__file__).parent.parent / path)


settings = Settings()
DATABASE_URL = f'{settings.DB_CONNECTION}://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}'
