from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    PORT: int = 5000
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"

    AUTH_SERVICE_URL: str = "http://auth-service:5001"
    USER_SERVICE_URL: str = "http://user-service:5002"
    MOVIE_SERVICE_URL: str = "http://movie-service:5003"
    VOUCHER_SERVICE_URL: str = "http://voucher-service:5004"
    BOOKING_SERVICE_URL: str = "http://booking-service:5005"
    PAYMENT_SERVICE_URL: str = "http://payment-service:5006"

    HTTP_TIMEOUT_SECONDS: float = 15.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
