# Frontend — Cinema Booking UI

React + Vite + TypeScript single-page app that drives the cinema ticket
booking flow. All traffic is routed through the API Gateway.

## Tech Stack

| Component        | Choice               |
|------------------|----------------------|
| Framework        | React 18 + TypeScript 5 |
| Build Tool       | Vite 5                |
| Router           | react-router-dom v6 (HashRouter) |
| HTTP             | axios                 |
| Tests            | vitest + @testing-library/react |
| Styling          | Single global CSS (dark theme) |
| Package Manager  | npm                   |

## Getting Started

```bash
# From the frontend directory
npm install
npm run dev        # http://localhost:5173

# Tests
npm run test

# Production build + preview
npm run build
npm run preview
```

Or via Docker Compose from the repo root:

```bash
docker compose up frontend --build
```

## Environment Variables

| Variable              | Description                | Default                  |
|-----------------------|----------------------------|--------------------------|
| `VITE_API_BASE_URL`   | URL of the API Gateway     | `http://localhost:5000`  |

The axios client reads this value at build time (Vite substitutes the
string) and all API calls are routed through it.

## Project Structure

```
frontend/
  Dockerfile
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api/           # axios client + per-service modules
    components/    # NavBar, PrivateRoute, SeatGrid
    context/       # AuthContext
    router/        # route definitions
    styles/        # global.css
    types/         # shared TS types
    views/         # one file per page (MovieList, MovieDetail, ShowtimeBooking, PaymentCheckout, ...)
  tests/           # vitest smoke tests
```

## Booking Flow

1. `GET /movies` on the home page -> click a movie -> `GET /movies/{id}`
2. Pick a showtime -> `GET /showtimes/{id}` + `GET /showtimes/{id}/seats`
3. Select seats, optionally apply a voucher (`POST /vouchers/validate`)
4. `POST /bookings` -> redirect to `/pay/{payment_id}`
5. "Pay" button calls `POST /payments/{id}/confirm { success: true }`
6. Redirect to `/booking/payment-result?booking_id=...` which polls
   `GET /bookings/{id}` every 2s (up to 15 tries) until a terminal status
   (`ACTIVE`, `CANCELLED`, `FAILED`).

## Notes

- All API calls go through the **API Gateway**, never directly to a
  backend service.
- Auth token is stored in `localStorage` under `token`; the axios
  interceptor adds `Authorization: Bearer <token>` automatically.
- Protected routes (`/bookings`, `/showtimes/:id/book`, `/pay/:id`,
  `/booking/payment-result`) redirect to `/login` when no token is
  present.
