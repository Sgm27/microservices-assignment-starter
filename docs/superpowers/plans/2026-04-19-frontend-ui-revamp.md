# Frontend UI Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dark frontend theme with a Premium Cinema (white + navy/sky blue) theme, fix poster images by serving them locally from `frontend/public/posters/`, and apply a consistent visual pass across all routes.

**Architecture:** All visual changes live in `frontend/src/styles/global.css` (rewritten design tokens) plus a new `MoviePoster` component with a graceful gradient fallback. Component templates remain mostly unchanged — only `MovieList`, `MovieDetail`, and `NavBar` get small structural edits. `services/movieService/seed.py` is updated to point posters to `/posters/<slug>.jpg` and to upsert `poster_url` on existing rows so the demo DB picks up new posters without a wipe.

**Tech Stack:** React 18 + Vite + TypeScript (frontend), CSS custom properties (no UI library), FastAPI + SQLAlchemy + PyMySQL (movieService), Docker Compose for orchestration.

**Spec:** `docs/superpowers/specs/2026-04-19-frontend-ui-revamp-design.md`

---

## File map

- **Create**
  - `frontend/src/components/MoviePoster.tsx` — image with `onError` fallback to gradient div
  - `frontend/public/posters/.gitkeep` — committed marker so the directory exists in fresh clones
- **Modify**
  - `frontend/src/styles/global.css` — full token rewrite + new utility classes (`.hero`, `.poster-fallback`, badge tints, sticky navbar)
  - `frontend/src/components/NavBar.tsx` — brand gradient text, `NavLink` for active styling
  - `frontend/src/views/MovieList.tsx` — wrap grid in a `.hero` band, use `<MoviePoster>`
  - `frontend/src/views/MovieDetail.tsx` — replace inline poster `<img>`/placeholder with `<MoviePoster>`
  - `services/movieService/seed.py` — change poster URLs to `/posters/<slug>.jpg`, extend upsert to update `poster_url` on existing movies

---

## Task 1: Create posters public directory

**Files:**
- Create: `frontend/public/posters/.gitkeep`

- [ ] **Step 1: Create the directory marker**

```bash
mkdir -p frontend/public/posters
touch frontend/public/posters/.gitkeep
```

- [ ] **Step 2: Verify Vite serves the path**

```bash
ls frontend/public/posters/
```
Expected: `.gitkeep` listed.

(No image files yet — they'll be added by the user. Until then `MoviePoster` falls back to the gradient placeholder.)

- [ ] **Step 3: Commit**

```bash
git add frontend/public/posters/.gitkeep
git commit -m "chore(frontend): add public/posters/ for local movie posters"
```

---

## Task 2: Rewrite global.css with new tokens

**Files:**
- Modify: `frontend/src/styles/global.css` (full rewrite)

- [ ] **Step 1: Replace the file contents**

Overwrite `frontend/src/styles/global.css` with:

```css
:root {
  --bg: #f6f9ff;
  --surface: #ffffff;
  --surface-2: #eef3fb;
  --border: #dbe4f3;
  --text: #0b1f3a;
  --muted: #5b6b85;
  --primary: #1d4ed8;
  --primary-hover: #1e40af;
  --accent: #38bdf8;
  --success: #16a34a;
  --danger: #dc2626;
  --warn: #d97706;
  --gradient-hero: linear-gradient(135deg, #1e3a8a 0%, #38bdf8 100%);
  --shadow-sm: 0 1px 2px rgba(15, 40, 90, 0.06),
    0 1px 3px rgba(15, 40, 90, 0.08);
  --shadow-md: 0 4px 12px rgba(15, 40, 90, 0.1);
  --shadow-lg: 0 10px 30px rgba(15, 40, 90, 0.12);
  --radius: 12px;
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
  font-size: 15px;
  line-height: 1.5;
}

a {
  color: var(--primary);
  text-decoration: none;
}
a:hover {
  color: var(--primary-hover);
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.navbar .nav-left,
.navbar .nav-right {
  display: flex;
  gap: 20px;
  align-items: center;
}

.navbar a {
  color: var(--text);
  font-weight: 500;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}
.navbar a:hover {
  color: var(--primary);
}
.navbar a.active {
  color: var(--primary);
  border-bottom-color: var(--accent);
}

.brand {
  font-weight: 800;
  font-size: 20px;
  background: var(--gradient-hero);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  border-bottom: none !important;
}

.user-email {
  color: var(--muted);
  font-size: 13px;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px;
  width: 100%;
}

h1 {
  margin-top: 0;
  color: var(--text);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px;
  margin: 0 auto;
  box-shadow: var(--shadow-md);
}

.narrow {
  max-width: 420px;
}

.center {
  text-align: center;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}

input,
select,
textarea {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  width: 100%;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.15);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--surface-2);
  color: var(--text);
  transition: background 0.15s ease, transform 0.1s ease,
    box-shadow 0.15s ease;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: white;
  box-shadow: 0 2px 6px rgba(29, 78, 216, 0.25);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(29, 78, 216, 0.3);
}

.btn-ghost {
  background: var(--surface);
  border-color: var(--border);
  color: var(--text);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--surface-2);
  border-color: var(--primary);
  color: var(--primary);
}

.btn-link {
  background: transparent;
  border: none;
  padding: 0;
  color: var(--primary);
  cursor: pointer;
  font-size: inherit;
  font-weight: 600;
}

.btn-row {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
}

.muted {
  color: var(--muted);
  font-size: 13px;
}

.error {
  color: var(--danger);
  font-size: 13px;
}

.success {
  color: var(--success);
  font-size: 13px;
}

/* Hero band on MovieList */
.hero {
  background: var(--gradient-hero);
  color: white;
  border-radius: var(--radius);
  padding: 48px 32px;
  margin-bottom: 32px;
  box-shadow: var(--shadow-md);
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 32px;
  color: white;
}

.hero p {
  margin: 0;
  color: rgba(255, 255, 255, 0.85);
  font-size: 15px;
}

/* Movie grid */
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.movie-card {
  background: var(--surface);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  color: var(--text);
  box-shadow: var(--shadow-md);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.movie-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.movie-card img,
.movie-card .poster-fallback {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  display: block;
}

.poster-fallback {
  background: var(--gradient-hero);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  font-weight: 700;
  font-size: 18px;
  line-height: 1.3;
}

.poster-fallback.large {
  width: 240px;
  height: 360px;
  border-radius: var(--radius);
  font-size: 22px;
}

.movie-info {
  padding: 14px 16px 16px;
}

.movie-info h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: var(--text);
}

.genre-pill {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.15);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
}

/* Movie detail */
.movie-detail-top {
  display: flex;
  gap: 32px;
  margin-bottom: 32px;
  align-items: flex-start;
}

.movie-detail-top .poster {
  width: 240px;
  height: 360px;
  object-fit: cover;
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
}

.showtime-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.showtime-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
  width: 100%;
  padding: 14px 18px;
}

/* Seats */
.seat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(56px, 1fr));
  gap: 8px;
  max-width: 640px;
  margin: 16px 0;
}

.seat {
  padding: 10px 0;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.seat-available:hover {
  border-color: var(--primary);
  background: rgba(56, 189, 248, 0.1);
}

.seat-pending {
  background: #fff7ed;
  border-color: var(--warn);
  color: var(--warn);
  cursor: not-allowed;
  opacity: 0.7;
}

.seat-booked {
  background: var(--surface-2);
  color: var(--muted);
  cursor: not-allowed;
  text-decoration: line-through;
  opacity: 0.7;
}

.seat-selected {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.seat-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 16px;
  align-items: center;
}

.legend-box {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 3px;
  margin-right: 4px;
  vertical-align: middle;
  border: 1px solid var(--border);
}

.legend-box.seat-available {
  background: var(--surface);
}
.legend-box.seat-pending {
  background: #fff7ed;
  border-color: var(--warn);
}
.legend-box.seat-booked {
  background: var(--surface-2);
}
.legend-box.seat-selected {
  background: var(--primary);
  border-color: var(--primary);
}

.voucher-row {
  display: flex;
  gap: 8px;
  margin: 16px 0;
  max-width: 480px;
}

.booking-summary {
  background: var(--surface-2);
  padding: 18px 20px;
  border-radius: var(--radius);
  margin: 16px 0;
}

.booking-summary p {
  margin: 4px 0;
}

.booking-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.booking-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  box-shadow: var(--shadow-sm);
}

.booking-item > div {
  margin: 3px 0;
}

.badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 999px;
  background: var(--surface-2);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  color: var(--muted);
}

.badge-success {
  background: rgba(22, 163, 74, 0.12);
  border-color: var(--success);
  color: var(--success);
}

.badge-error {
  background: rgba(220, 38, 38, 0.12);
  border-color: var(--danger);
  color: var(--danger);
}
```

- [ ] **Step 2: Verify the file is syntactically valid**

Run from repo root:
```bash
node -e "const css = require('fs').readFileSync('frontend/src/styles/global.css', 'utf8'); console.log('chars:', css.length); console.log(css.match(/[{}]/g).reduce((a,c)=>a+(c==='{'?1:-1),0)===0 ? 'balanced braces' : 'UNBALANCED');"
```
Expected: prints char count and `balanced braces`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "style(frontend): rewrite global.css to white + navy/sky-blue theme"
```

---

## Task 3: Create MoviePoster component

**Files:**
- Create: `frontend/src/components/MoviePoster.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/MoviePoster.tsx`:

```tsx
import { useState } from "react";

type Props = {
  src?: string;
  title: string;
  className?: string;
  fallbackClassName?: string;
};

export default function MoviePoster({
  src,
  title,
  className,
  fallbackClassName,
}: Props) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    const cls = ["poster-fallback", fallbackClassName].filter(Boolean).join(" ");
    return (
      <div className={cls}>
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

- [ ] **Step 2: Verify it compiles**

```bash
docker compose build frontend
```
Expected: build succeeds (the Dockerfile runs `npm run build`, which runs `tsc -b && vite build`, so type errors fail the build). The runtime container does not include `src/` or `tsconfig.json`, which is why we use `build` rather than `tsc --noEmit` in a `run`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MoviePoster.tsx
git commit -m "feat(frontend): add MoviePoster component with gradient fallback"
```

---

## Task 4: Update NavBar with brand gradient and active link

**Files:**
- Modify: `frontend/src/components/NavBar.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/components/NavBar.tsx`:

```tsx
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="nav-left">
        <NavLink to="/" className="brand" end>
          🎬 CinemaBox
        </NavLink>
        <NavLink
          to="/"
          end
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Home
        </NavLink>
        {isAuthenticated && (
          <NavLink
            to="/bookings"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            My Bookings
          </NavLink>
        )}
      </div>
      <div className="nav-right">
        {isAuthenticated ? (
          <>
            <span className="user-email">{user?.email}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="btn btn-ghost"
            >
              Logout
            </button>
          </>
        ) : (
          <NavLink to="/login" className="btn btn-primary">
            Login
          </NavLink>
        )}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Type-check via build**

```bash
docker compose build frontend
```
Expected: build succeeds (TypeScript errors would fail `npm run build`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NavBar.tsx
git commit -m "feat(frontend): NavBar gradient brand + active route underline"
```

---

## Task 5: Update MovieList — hero band + MoviePoster

**Files:**
- Modify: `frontend/src/views/MovieList.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/MovieList.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMovies } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import type { Movie } from "../types";

export default function MovieList() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    listMovies()
      .then((data) => {
        if (mounted) setMovies(data);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ?? "Failed to load movies",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <p>Loading movies…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <div className="hero">
        <h1>Now Showing</h1>
        <p>Pick a film and book your seat in seconds.</p>
      </div>
      {movies.length === 0 ? (
        <p className="muted">No movies available.</p>
      ) : (
        <div className="movie-grid">
          {movies.map((m) => (
            <Link key={m.id} to={`/movies/${m.id}`} className="movie-card">
              <MoviePoster src={m.poster_url} title={m.title} />
              <div className="movie-info">
                <h3>{m.title}</h3>
                <p className="muted">
                  {m.duration_minutes ? `${m.duration_minutes} min` : ""}
                  {m.duration_minutes && (m as { genre?: string }).genre
                    ? " · "
                    : ""}
                  {(m as { genre?: string }).genre && (
                    <span className="genre-pill">
                      {(m as { genre?: string }).genre}
                    </span>
                  )}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
```

Note on `genre`: the backend returns `genre` (see `MovieListItem`) but the existing `Movie` type doesn't declare it. We read it through a narrow inline cast to avoid touching `types/index.ts` for an optional cosmetic field — keeping the change scoped. (If you'd rather add `genre?: string` to `Movie`, do it in this same task and remove the casts.)

- [ ] **Step 2: Type-check via build**

```bash
docker compose build frontend
```
Expected: build succeeds (TypeScript errors would fail `npm run build`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MovieList.tsx
git commit -m "feat(frontend): MovieList hero band + MoviePoster fallback"
```

---

## Task 6: Update MovieDetail to use MoviePoster

**Files:**
- Modify: `frontend/src/views/MovieDetail.tsx` (poster block only)

- [ ] **Step 1: Edit the poster block**

In `frontend/src/views/MovieDetail.tsx`, change the import block at the top to add `MoviePoster`:

Replace:
```tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie } from "../api/movies";
import type { Movie } from "../types";
```

With:
```tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import type { Movie } from "../types";
```

Then replace the existing poster ternary:

```tsx
        {movie.poster_url ? (
          <img src={movie.poster_url} alt={movie.title} className="poster" />
        ) : (
          <div className="poster-placeholder large">{movie.title}</div>
        )}
```

With:

```tsx
        <MoviePoster
          src={movie.poster_url}
          title={movie.title}
          className="poster"
          fallbackClassName="large"
        />
```

- [ ] **Step 2: Type-check via build**

```bash
docker compose build frontend
```
Expected: build succeeds (TypeScript errors would fail `npm run build`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MovieDetail.tsx
git commit -m "feat(frontend): MovieDetail uses MoviePoster fallback"
```

---

## Task 7: Update movie seed — local poster URLs + upsert poster_url

**Files:**
- Modify: `services/movieService/seed.py`

The current seed is idempotent and skips existing movies — so changing `poster_url` constants alone wouldn't update DB rows that were seeded before. We need a small upsert tweak.

- [ ] **Step 1: Update poster_url values**

In `services/movieService/seed.py`, replace each TMDB URL in `SEED_MOVIES` so that each entry's `poster_url` becomes `/posters/<slug>.jpg`:

| Title | New `poster_url` |
| --- | --- |
| `Oppenheimer` | `/posters/oppenheimer.jpg` |
| `Inside Out 2` | `/posters/inside-out-2.jpg` |
| `Dune: Part Two` | `/posters/dune-part-two.jpg` |

Concretely, in the `SEED_MOVIES` list change the three lines:
```python
"poster_url": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
"poster_url": "https://image.tmdb.org/t/p/w500/vpnVM9B6NMmQpWeZvzLvDESb2QE.jpg",
"poster_url": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
```
to:
```python
"poster_url": "/posters/oppenheimer.jpg",
"poster_url": "/posters/inside-out-2.jpg",
"poster_url": "/posters/dune-part-two.jpg",
```

- [ ] **Step 2: Make the upsert update poster_url on existing rows**

Locate this block in the `seed()` function:

```python
            movie = session.query(Movie).filter_by(title=movie_data["title"]).first()
            if movie is None:
                movie = Movie(**movie_data)
                session.add(movie)
                session.flush()
                created_movies += 1
```

Replace with:

```python
            movie = session.query(Movie).filter_by(title=movie_data["title"]).first()
            if movie is None:
                movie = Movie(**movie_data)
                session.add(movie)
                session.flush()
                created_movies += 1
            else:
                # Refresh mutable fields so re-running picks up new posters etc.
                for field in ("description", "duration_min", "poster_url", "genre"):
                    new_value = movie_data.get(field)
                    if new_value is not None and getattr(movie, field) != new_value:
                        setattr(movie, field, new_value)
```

- [ ] **Step 3: Re-run the seed against the running stack**

```bash
docker compose up -d mysql-db movie-service
docker compose run --rm --no-deps \
    -v "$(pwd)/services/movieService/seed.py:/app/seed.py" \
    movie-service python seed.py
```
Expected output: `[movieService] seeded 0 movies, 0 showtimes, 0 seats` (counts may be >0 on a fresh DB). Check that the command exits 0.

- [ ] **Step 4: Verify the API now serves local poster URLs**

```bash
curl -fsS http://localhost:5003/movies | python3 -c "import json,sys; data=json.load(sys.stdin); [print(m['id'], m['title'], '->', m['poster_url']) for m in data]"
```
Expected: every row's `poster_url` starts with `/posters/`. (Hitting the service directly avoids the gateway and JWT.)

- [ ] **Step 5: Commit**

```bash
git add services/movieService/seed.py
git commit -m "feat(movieService): seed posters from local /posters/ + upsert mutable fields"
```

---

## Task 8: Build verification

**Files:**
- (none)

- [ ] **Step 1: Build the frontend image**

```bash
docker compose build frontend
```
Expected: build succeeds, no TS errors.

- [ ] **Step 2: Bring up the full stack**

```bash
docker compose up -d
```
Expected: all containers report healthy after a few seconds.

- [ ] **Step 3: Hit the gateway health endpoint**

```bash
curl -fsS http://localhost:5000/health
```
Expected: `{"status":"ok"}` or similar non-empty 2xx.

---

## Task 9: Manual visual verification

**Files:**
- (none — runtime check)

- [ ] **Step 1: Open `http://localhost:5173/`**

Confirm:
- White background with hero band gradient (navy → sky blue) at the top
- "Now Showing" title in white inside the hero
- Card grid below: 4 columns on a wide window, with shadow and hover lift
- Each card shows either a real poster (if user added the JPGs) **or** a gradient fallback with the movie title in white — no broken-image icon

- [ ] **Step 2: Click a movie**

Navigate to `/movies/<id>`. Confirm:
- Large poster (or large gradient fallback) on the left, info on the right
- Showtime list renders as ghost-style buttons with hover

- [ ] **Step 3: Sign in (or register), then click a showtime**

Confirm on `/showtimes/<id>/book`:
- Seat grid with white available seats (border highlights blue on hover)
- Selected seats turn solid primary blue with white text
- Legend boxes match the seat states
- Voucher input + Book button render with the new style

- [ ] **Step 4: Pay (mock) and view bookings**

Confirm:
- `/mock-pay/...`: centered card with primary Pay button
- `/booking/payment-result`: status badge tinted green/red/amber depending on status
- `/bookings`: list of cards with shadow

- [ ] **Step 5: Try the responsive layout**

Resize the window down to ~600px wide. Grid should reflow to 2 columns; navbar should stay readable.

- [ ] **Step 6: Note follow-ups (optional)**

If any view still looks "dark-themed" (leftover hard-coded color), capture the file:line and add a small follow-up commit.

---

## Out of scope (do NOT do in this plan)

- Adding poster `.jpg` files (user provides them)
- Adding a dark-mode toggle
- Refactoring the API client or auth flow
- Backend changes other than the seed file
- Adding new product features (search, filters, etc.)
