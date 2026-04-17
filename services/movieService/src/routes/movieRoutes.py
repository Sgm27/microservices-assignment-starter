from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import movieController
from ..validators.movieSchemas import MovieDetail, MovieListItem, ShowtimeDetail

router = APIRouter(tags=["movies"])


@router.get("/movies", response_model=list[MovieListItem])
def list_movies(db: Session = Depends(get_db)) -> list[MovieListItem]:
    return movieController.list_movies(db)


@router.get("/movies/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: int, db: Session = Depends(get_db)) -> MovieDetail:
    return movieController.get_movie(db, movie_id)


@router.get("/showtimes/{showtime_id}", response_model=ShowtimeDetail)
def get_showtime(showtime_id: int, db: Session = Depends(get_db)) -> ShowtimeDetail:
    return movieController.get_showtime(db, showtime_id)
