# movieService

Owns movies, showtimes, and seats for the cinema booking flow.

- **Port**: 5003
- **DB**: `movie_db`

## Endpoints

| Method | Path                            | Description                                           |
| ------ | ------------------------------- | ----------------------------------------------------- |
| GET    | /health                         | health check                                          |
| GET    | /movies                         | list movies                                           |
| GET    | /movies/{id}                    | movie detail + nested showtimes                       |
| GET    | /showtimes/{id}                 | showtime detail + movie summary                       |
| GET    | /showtimes/{id}/seats           | list seats for a showtime                             |
| POST   | /seats/reserve                  | reserve seats (AVAILABLE -> PENDING)                  |
| POST   | /seats/confirm                  | confirm reserved seats (PENDING -> BOOKED)            |
| POST   | /seats/release                  | release reserved seats (PENDING -> AVAILABLE)         |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5003
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
