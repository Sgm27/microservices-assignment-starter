from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    PORT: int = 5005

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "booking_db"
    SQLALCHEMY_URL: Optional[str] = None

    MOVIE_SERVICE_URL: str = "http://movie-service:5003"
    VOUCHER_SERVICE_URL: str = "http://voucher-service:5004"
    PAYMENT_SERVICE_URL: str = "http://payment-service:5006"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:5007"

    TEMPORAL_HOST: str = "temporal:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "booking-task-queue"

    PAYMENT_POLL_INTERVAL_SECONDS: int = 5
    PAYMENT_TIMEOUT_SECONDS: int = 300

    HTTP_TIMEOUT_SECONDS: float = 10.0

    @property
    def database_url(self) -> str:
        if self.SQLALCHEMY_URL:
            return self.SQLALCHEMY_URL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
