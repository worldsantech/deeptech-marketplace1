import os
from functools import lru_cache


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.APP_NAME = os.getenv("APP_NAME", "DeepTech Marketplace API")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
        self.ENV = os.getenv("ENV", "development").strip().lower()
        self.DEBUG = _as_bool(os.getenv("DEBUG"), default=self.ENV != "production")

        self.SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
        self.DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

        self.CORS_ALLOW_ORIGINS = [
            item.strip()
            for item in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
            if item.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    def validate(self) -> None:
        if self.is_production:
            if not self.DATABASE_URL:
                raise RuntimeError("DATABASE_URL is required in production")

            if self.SECRET_KEY == "changeme":
                raise RuntimeError("SECRET_KEY must not use the default value in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings