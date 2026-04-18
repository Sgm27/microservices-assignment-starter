"""Seed movie_db with sample movies, showtimes, and seats.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/movieService/seed.py:/app/seed.py \
        movie-service python seed.py

Idempotent: matches movies by title; skips creating duplicates.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from src.config.database import Base, SessionLocal, engine
from src.models.movieModel import Movie
from src.models.seatModel import Seat
from src.models.showtimeModel import Showtime

ROWS = ["A", "B", "C"]
COLS = 10  # 30 seats per showtime: A1..A10, B1..B10, C1..C10


def _seat_numbers() -> list[str]:
    return [f"{row}{col}" for row in ROWS for col in range(1, COLS + 1)]


# showtimes are relative to "now" so the demo stays fresh.
def _in_days(days: int, hour: int = 19, minute: int = 0) -> datetime:
    now = datetime.utcnow().replace(microsecond=0)
    return (now + timedelta(days=days)).replace(hour=hour, minute=minute, second=0)


SEED_MOVIES = [
    {
        "title": "Oppenheimer",
        "description": "The story of J. Robert Oppenheimer and the atomic bomb.",
        "duration_min": 180,
        "poster_url": "/posters/oppenheimer.jpg",
        "genre": "Drama",
        "showtimes": [
            {"room": "Hall-1", "starts_at": _in_days(1, 19), "base_price": Decimal("120000")},
            {"room": "Hall-2", "starts_at": _in_days(2, 21), "base_price": Decimal("120000")},
        ],
    },
    {
        "title": "Inside Out 2",
        "description": "Riley's teenage emotions move into headquarters.",
        "duration_min": 96,
        "poster_url": "/posters/inside-out-2.jpg",
        "genre": "Animation",
        "showtimes": [
            {"room": "Hall-1", "starts_at": _in_days(1, 14), "base_price": Decimal("90000")},
            {"room": "Hall-3", "starts_at": _in_days(3, 17), "base_price": Decimal("95000")},
        ],
    },
    {
        "title": "Dune: Part Two",
        "description": "Paul Atreides unites with the Fremen to seek revenge.",
        "duration_min": 166,
        "poster_url": "/posters/dune-part-two.jpg",
        "genre": "Sci-Fi",
        "showtimes": [
            {"room": "IMAX-1", "starts_at": _in_days(2, 20), "base_price": Decimal("180000")},
        ],
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created_movies = 0
    created_showtimes = 0
    created_seats = 0
    try:
        for movie_data in SEED_MOVIES:
            showtimes_data = movie_data.pop("showtimes")
            movie = session.query(Movie).filter_by(title=movie_data["title"]).first()
            if movie is None:
                movie = Movie(**movie_data)
                session.add(movie)
                session.flush()
                created_movies += 1
            else:
                # Refresh mutable fields so re-running picks up new posters etc.
                for field in ("description", "duration_min", "poster_url", "genre"):
                    new_value = movie_data.get(field)
                    if new_value is not None and getattr(movie, field) != new_value:
                        setattr(movie, field, new_value)

            for st_data in showtimes_data:
                showtime = (
                    session.query(Showtime)
                    .filter_by(
                        movie_id=movie.id,
                        room=st_data["room"],
                        starts_at=st_data["starts_at"],
                    )
                    .first()
                )
                if showtime is None:
                    showtime = Showtime(
                        movie_id=movie.id,
                        total_seats=len(_seat_numbers()),
                        **st_data,
                    )
                    session.add(showtime)
                    session.flush()
                    created_showtimes += 1

                    for seat_num in _seat_numbers():
                        session.add(
                            Seat(
                                showtime_id=showtime.id,
                                seat_number=seat_num,
                                status="AVAILABLE",
                            )
                        )
                        created_seats += 1
        session.commit()
    finally:
        session.close()

    print(
        f"[movieService] seeded {created_movies} movies, "
        f"{created_showtimes} showtimes, {created_seats} seats"
    )


if __name__ == "__main__":
    seed()
