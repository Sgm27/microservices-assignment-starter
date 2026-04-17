from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import Base, engine
from .models import userModel  # noqa: F401  ensure model is registered
from .routes.userRoutes import router as user_router


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="User Service", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(user_router)
    return app


app = create_app()
