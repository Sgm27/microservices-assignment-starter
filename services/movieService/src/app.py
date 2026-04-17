from datetime import datetime, time, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import Base, SessionLocal, engine
from .models import movieModel, seatModel, showtimeModel  # noqa: F401  register models
from .models.movieModel import Movie
from .models.seatModel import Seat
from .models.showtimeModel import Showtime
from .routes.movieRoutes import router as movie_router
from .routes.seatRoutes import seat_router, showtime_seat_router


SEED_MOVIES = [
    {
        "title": "Dune: Part Two",
        "description": "Paul Atreides unites with the Fremen to seek revenge against those who destroyed his family.",
        "duration_min": 166,
        "genre": "Sci-Fi",
        "poster_url": "https://example.com/posters/dune2.jpg",
    },
    {
        "title": "Inside Out 2",
        "description": "Riley's emotions face new feelings as she enters her teen years.",
        "duration_min": 96,
        "genre": "Animation",
        "poster_url": "https://example.com/posters/insideout2.jpg",
    },
    {
        "title": "The Batman",
        "description": "Batman tracks down the Riddler across the streets of Gotham.",
        "duration_min": 176,
        "genre": "Action",
        "poster_url": "https://example.com/posters/thebatman.jpg",
    },
]

SEED_ROWS = ["A", "B", "C"]
SEED_COLS = list(range(1, 11))


def _seed_database() -> None:
    session = SessionLocal()
    try:
        existing = session.query(Movie).count()
        if existing > 0:
            return

        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        showtime_plan = [
            (datetime.combine(today, time(18, 0)), "Room 1"),
            (datetime.combine(tomorrow, time(20, 0)), "Room 2"),
        ]
        prices = [Decimal("80000.00"), Decimal("100000.00"), Decimal("120000.00")]

        for movie_idx, spec in enumerate(SEED_MOVIES):
            movie = Movie(**spec)
            session.add(movie)
            session.flush()

            for st_idx, (starts_at, room) in enumerate(showtime_plan):
                price = prices[(movie_idx + st_idx) % len(prices)]
                showtime = Showtime(
                    movie_id=movie.id,
                    room=room,
                    starts_at=starts_at,
                    base_price=price,
                    total_seats=len(SEED_ROWS) * len(SEED_COLS),
                )
                session.add(showtime)
                session.flush()

                for row in SEED_ROWS:
                    for col in SEED_COLS:
                        session.add(
                            Seat(
                                showtime_id=showtime.id,
                                seat_number=f"{row}{col}",
                                status="AVAILABLE",
                            )
                        )

        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    try:
        _seed_database()
    except Exception:
        pass

    app = FastAPI(title="Movie Service", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(movie_router)
    app.include_router(showtime_seat_router)
    app.include_router(seat_router)
    return app


app = create_app()
