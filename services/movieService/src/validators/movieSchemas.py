from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ShowtimeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room: str
    starts_at: datetime
    base_price: Decimal


class MovieSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    duration_min: int
    genre: str | None = None
    poster_url: str | None = None


class MovieListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    duration_min: int
    poster_url: str | None = None
    genre: str | None = None


class MovieDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    duration_min: int
    poster_url: str | None = None
    genre: str | None = None
    showtimes: list[ShowtimeSummary] = []


class ShowtimeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room: str
    starts_at: datetime
    base_price: Decimal
    total_seats: int
    movie: MovieSummary
