from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.proxyRoutes import router as proxy_router


def create_app() -> FastAPI:
    app = FastAPI(title="API Gateway", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(proxy_router)
    return app


app = create_app()
