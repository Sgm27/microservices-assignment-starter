# CLAUDE.md — Cinema Ticket Booking

> Microservices project — single business flow: book a movie ticket.
> Stack: FastAPI (Python 3.11) + React + Vite + TypeScript + Temporal + MySQL.
> Run with: `docker compose up --build`

## Architecture (high level)

- **Frontend** (5173) — React + Vite + TS
- **Gateway** (5000) — FastAPI proxy + JWT verify
- **authService** (5001) — login, register, JWT issuance
- **userService** (5002) — user profile CRUD
- **movieService** (5003) — movies, showtimes, seats
- **voucherService** (5004) — discount code validation
- **bookingService** (5005) — Temporal workflow orchestrator (start/query/cancel)
- **paymentService** (5006) — VNPay sandbox / mock
- **notificationService** (5007) — email via Temporal activity
- **mysql-db** (3307→3306) — one schema per service
- **temporal** (7233) + **temporal-ui** (8088→8080) — workflow engine

## Single business flow

`POST /bookings` → bookingService starts Temporal workflow `BookingWorkflow`:

1. Activity `reserve_seat` → movieService (lock seat row in PENDING)
2. Activity `validate_voucher` → voucherService (compute discount)
3. Activity `create_payment` → paymentService (return VNPay URL or mock URL)
4. Workflow waits for signal `payment_completed` (sent by paymentService webhook)
5. On SUCCESS: activity `confirm_seat` + `send_notification`
6. On FAILURE/timeout: compensating activity `release_seat` + `cancel_payment`

## Key Rules

- Every service exposes `GET /health` → `{"status": "ok"}`
- Services communicate via Docker Compose DNS (service names, not localhost)
- Each service owns its own MySQL schema (DB-per-service)
- Use environment variables — no hardcoded secrets
- All services are FastAPI, use SQLAlchemy + PyMySQL, expose OpenAPI at `/docs`
- Tests live in `services/<svc>/tests/` and run with `pytest`

## Service folder convention (FastAPI)

```
services/<svcName>/
  Dockerfile
  pyproject.toml          # or requirements.txt
  src/
    __init__.py
    app.py                # FastAPI app factory + include routers
    main.py               # uvicorn entry
    config/               # settings.py (pydantic-settings), database.py
    controllers/          # business logic
    routes/               # APIRouter definitions
    models/               # SQLAlchemy ORM
    helpers/              # shared utilities (optional)
    validators/           # pydantic schemas (optional)
    middleware/           # request middleware (optional)
    workers/              # background workers (notification only)
    services/             # service-layer (notification only)
    workflows/            # Temporal workflow defs (booking only)
    activities/           # Temporal activity defs (booking only)
  tests/
    test_*.py
```

## When making changes

1. Update OpenAPI specs in `docs/api-specs/` when adding endpoints
2. Update `services/<svc>/readme.md` when changing behavior
3. Run `make test-service s=<svcName>` to verify
4. Run `docker compose build <service>` to verify container builds
