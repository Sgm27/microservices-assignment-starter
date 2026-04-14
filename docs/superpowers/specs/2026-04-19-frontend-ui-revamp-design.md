# Frontend UI Revamp — Premium Cinema (White + Blue)

**Date:** 2026-04-19
**Scope:** `frontend/` + minor change in `services/movieService/seed.py`
**Goal:** Replace dark theme with a light "Premium Cinema" theme (white surfaces, navy text, navy→sky-blue gradient accents, soft shadows). Fix broken poster images by switching to local files served from `frontend/public/posters/`.

## Motivation

Current UI is dark with thin borders and broken TMDB-hosted posters. User wants:
1. Posters to render reliably.
2. White + blue palette (navy/sky-blue gradient, shadow-based depth).
3. A consistent visual pass across all pages.

## Design tokens (CSS variables in `global.css`)

```
--bg:        #f6f9ff     /* off-white page background */
--surface:   #ffffff     /* card background */
--surface-2: #eef3fb     /* input/seat background */
--border:    #dbe4f3
--text:      #0b1f3a     /* navy text */
--muted:     #5b6b85
--primary:   #1d4ed8     /* primary blue (buttons, links) */
--primary-hover: #1e40af
--accent:    #38bdf8     /* sky blue (hover/highlight) */
--success:   #16a34a
--danger:    #dc2626
--warn:      #d97706
--gradient-hero: linear-gradient(135deg, #1e3a8a 0%, #38bdf8 100%)
--shadow-sm: 0 1px 2px rgba(15,40,90,.06), 0 1px 3px rgba(15,40,90,.08)
--shadow-md: 0 4px 12px rgba(15,40,90,.10)
--shadow-lg: 0 10px 30px rgba(15,40,90,.12)
--radius:    12px
```

## Layout

- **Container** widens from 960px → 1100px.
- **Navbar**: white, sticky top, `box-shadow: var(--shadow-sm)`. Brand text uses `--gradient-hero` via `background-clip: text`. Active route gets a 2px sky-blue underline.
- **Body** uses `--bg`. Default text `--text`.
- **Footer**: small muted "© 2026 CinemaBox".

## MovieList page

- **Hero band** above the grid:
  - Background: `--gradient-hero`.
  - Padding: `48px 32px`, border-radius `var(--radius)`, margin-bottom 32px.
  - Title `Now Showing` (white, 32px bold) + subtitle "Pick a film and book your seat" (white/80%).
- **Grid**: `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));` gap 20px.
- **Card** (`movie-card`):
  - Background `--surface`, `border-radius: var(--radius)`, `box-shadow: var(--shadow-md)`, no border.
  - Hover: `transform: translateY(-4px); box-shadow: var(--shadow-lg);`.
  - Poster: 2:3 aspect ratio (height auto via `aspect-ratio: 2/3`), `object-fit: cover`.
  - Info block padding 14px: title bold navy 16px; meta row with duration + genre badge (sky-blue tinted pill).

## MoviePoster component (new)

Path: `frontend/src/components/MoviePoster.tsx`.

```tsx
type Props = { src?: string; title: string; className?: string };

export default function MoviePoster({ src, title, className }: Props) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className={`poster-fallback ${className ?? ""}`}>
        <span>{title}</span>
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={title}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
```

`.poster-fallback` styles: `--gradient-hero` background, white text centered, padding, font-weight 700, line-clamp 3.

Used by `MovieList` (card poster) and `MovieDetail` (large poster).

## Image source migration

- Create `frontend/public/posters/` (committed, but actual `.jpg` files will be added by user).
- Add `frontend/public/posters/.gitkeep`.
- Update `services/movieService/seed.py` `SEED_MOVIES` so each `poster_url` is `/posters/<slug>.jpg`:
  - `Oppenheimer` → `/posters/oppenheimer.jpg`
  - `Inside Out 2` → `/posters/inside-out-2.jpg`
  - `Dune: Part Two` → `/posters/dune-part-two.jpg`
- Vite serves `public/` at root, so the gateway never sees these requests — they're loaded directly by the browser from the frontend container.
- After change the user must re-run the movie seed (idempotent matches by title; posters of existing rows must be updated → see "Open consideration" below).
- **Open consideration:** seed is idempotent and skips existing movies, so it will NOT update `poster_url` of already-seeded rows. The implementation plan must either (a) extend the seed to update `poster_url` on existing matches, or (b) instruct the user to truncate movies. Plan should pick (a) — least disruptive.

## Other pages (visual pass — same tokens, no behavioral change)

- **Login / Register**: card centered (max-width 420px), `--shadow-lg`, inputs use `--surface-2` background, focus ring `--primary`. Submit button `--primary` with hover `--primary-hover`.
- **MovieDetail**:
  - `.movie-detail-top`: poster left (240×360, `MoviePoster` component, `--shadow-md`), info right.
  - Showtime list: each entry is a pill button with hover `--accent` border.
- **ShowtimeBooking**:
  - Seat states:
    - `available`: white bg, `--border`, hover border `--primary`.
    - `selected`: `--primary` bg, white text.
    - `pending`: `#fff7ed` bg, `--warn` border, dimmed.
    - `booked`: `--surface-2` bg, line-through, dimmed.
  - Voucher input row + summary card use `--surface-2` panel.
- **MyBookings**: list of cards (`--surface`, `--shadow-sm`); status badge:
  - SUCCESS → green tint pill.
  - FAILED → red tint pill.
  - PENDING → amber tint pill.
- **PaymentResult / MockPay**: large status icon (emoji or unicode), centered card, primary CTA back to bookings.

## Files changed

- `frontend/src/styles/global.css` — rewrite tokens + new `.movie-card`, `.poster-fallback`, `.hero`, badge variants.
- `frontend/src/components/MoviePoster.tsx` — new component.
- `frontend/src/components/NavBar.tsx` — brand styling, sticky, active-link class.
- `frontend/src/views/MovieList.tsx` — add hero, use `MoviePoster`.
- `frontend/src/views/MovieDetail.tsx` — use `MoviePoster` for large poster.
- `frontend/src/views/ShowtimeBooking.tsx` — class adjustments only if needed for new seat states (CSS does most of the work via existing class names).
- `frontend/src/views/MyBookings.tsx` — badge class adjustments.
- `frontend/src/views/PaymentResult.tsx`, `MockPay.tsx`, `Login.tsx` — minor class touch-ups.
- `frontend/public/posters/.gitkeep` — directory marker.
- `services/movieService/seed.py` — change `poster_url` values + extend upsert logic so existing movies get the new poster path.

## Out of scope

- Dark mode toggle.
- Internationalization.
- Animation libraries (framer-motion, etc.).
- Backend changes other than the seed file.
- New product features (search, filters, ratings, etc.).

## Risks / considerations

- **User must add poster JPG files** to `frontend/public/posters/` (3 files for current seed). Until then the gradient fallback shows — this is acceptable and visually consistent.
- **Seed update on existing rows**: implementation plan must update `poster_url` on already-seeded movies, otherwise re-seeding is a no-op.
- **No automated visual regression**: success is "user opens in browser and confirms". The implementation plan must include a manual verification step (frontend dev container up, navigate each route, inspect).

## Success criteria

1. Visiting `/` shows the hero band + grid of cards with poster (or branded gradient fallback) — no broken-image icon.
2. All routes render with white surfaces, navy text, sky-blue accents — no leftover dark surfaces.
3. After user adds the 3 poster JPGs and re-runs the movie seed, real posters appear without code changes.
4. `npm run build` (or `docker compose build frontend`) succeeds with zero TypeScript errors.
