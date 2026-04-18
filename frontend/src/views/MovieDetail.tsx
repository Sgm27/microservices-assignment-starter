import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import type { Movie } from "../types";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function MovieDetail() {
  const { id } = useParams<{ id: string }>();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    setLoading(true);
    getMovie(id)
      .then((data) => {
        if (mounted) setMovie(data);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ?? "Failed to load movie",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) return <p>Loading movie…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!movie) return <p>Movie not found.</p>;

  const showtimes = movie.showtimes ?? [];

  return (
    <section className="movie-detail">
      <div className="movie-detail-top">
        <MoviePoster
          src={movie.poster_url}
          title={movie.title}
          className="poster"
          fallbackClassName="large"
        />
        <div>
          <h1>{movie.title}</h1>
          {movie.duration_minutes && (
            <p className="muted">{movie.duration_minutes} min</p>
          )}
          {movie.description && <p>{movie.description}</p>}
        </div>
      </div>

      <h2>Showtimes</h2>
      {showtimes.length === 0 ? (
        <p className="muted">No showtimes scheduled.</p>
      ) : (
        <ul className="showtime-list">
          {showtimes.map((s) => (
            <li key={s.id}>
              <Link
                to={`/showtimes/${s.id}/book`}
                className="showtime-card btn btn-ghost"
              >
                <span>{formatDate(s.starts_at)}</span>
                <span className="muted">Room {s.room}</span>
                <span>${Number(s.base_price).toFixed(2)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
