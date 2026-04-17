from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import Base, engine
from .models import paymentModel  # noqa: F401  ensure model is registered
from .routes.paymentRoutes import router as payments_router


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Payment Service", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(payments_router)
    return app


app = create_app()
