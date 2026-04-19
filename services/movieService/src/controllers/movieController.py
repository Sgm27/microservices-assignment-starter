from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from ..models.movieModel import Movie
from ..models.showtimeModel import Showtime
from ..validators.movieSchemas import (
    MovieDetail,
    MovieListItem,
    MovieSummary,
    ShowtimeDetail,
    ShowtimeSummary,
)


def list_movies(db: Session) -> list[MovieListItem]:
    movies = db.query(Movie).order_by(Movie.id).all()
    return [MovieListItem.model_validate(m) for m in movies]


def get_movie(db: Session, movie_id: int) -> MovieDetail:
    movie = (
        db.query(Movie)
        .options(selectinload(Movie.showtimes))
        .filter(Movie.id == movie_id)
        .first()
    )
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phim")

    return MovieDetail(
        id=movie.id,
        title=movie.title,
        description=movie.description,
        duration_min=movie.duration_min,
        poster_url=movie.poster_url,
        genre=movie.genre,
        showtimes=[ShowtimeSummary.model_validate(s) for s in movie.showtimes],
    )


def get_showtime(db: Session, showtime_id: int) -> ShowtimeDetail:
    showtime = (
        db.query(Showtime)
        .options(selectinload(Showtime.movie))
        .filter(Showtime.id == showtime_id)
        .first()
    )
    if not showtime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy suất chiếu")

    return ShowtimeDetail(
        id=showtime.id,
        room=showtime.room,
        starts_at=showtime.starts_at,
        base_price=showtime.base_price,
        total_seats=showtime.total_seats,
        movie=MovieSummary.model_validate(showtime.movie),
    )
