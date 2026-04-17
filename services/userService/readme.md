# userService

User profile CRUD for the cinema-booking microservices project.

- **Port**: 5002
- **DB**: `user_db.users`

## Endpoints

| Method | Path          | Description                                       |
| ------ | ------------- | ------------------------------------------------- |
| GET    | /health       | health check                                      |
| POST   | /users        | create user (optional explicit `id` from authSvc) |
| GET    | /users/{id}   | fetch user by id                                  |
| GET    | /users        | list all users                                    |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5002
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
