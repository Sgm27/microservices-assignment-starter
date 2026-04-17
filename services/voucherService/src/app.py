from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import Base, SessionLocal, engine
from .models import voucherModel  # noqa: F401  ensure model is registered
from .models.voucherModel import Voucher
from .routes.voucherRoutes import router as voucher_router


def _seed_vouchers() -> None:
    try:
        db = SessionLocal()
        try:
            count = db.query(Voucher).count()
            if count > 0:
                return
            now = datetime.utcnow()
            db.add_all(
                [
                    Voucher(
                        code="WELCOME10",
                        discount_percent=10,
                        max_uses=1000,
                        used_count=0,
                        valid_from=now - timedelta(days=1),
                        valid_to=now + timedelta(days=365),
                    ),
                    Voucher(
                        code="SUMMER50",
                        discount_percent=50,
                        max_uses=10,
                        used_count=0,
                        valid_from=now - timedelta(days=1),
                        valid_to=now + timedelta(days=30),
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        # Seeding is best-effort (e.g. DB not reachable during some test setups).
        pass


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    _seed_vouchers()

    app = FastAPI(title="Voucher Service", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(voucher_router)
    return app


app = create_app()
