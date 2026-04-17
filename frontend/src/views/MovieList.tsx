import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMovies } from "../api/movies";
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
  if (!movies.length) return <p>No movies available.</p>;

  return (
    <section>
      <h1>Now Showing</h1>
      <div className="movie-grid">
        {movies.map((m) => (
          <Link key={m.id} to={`/movies/${m.id}`} className="movie-card">
            {m.poster_url ? (
              <img src={m.poster_url} alt={m.title} />
            ) : (
              <div className="poster-placeholder">{m.title}</div>
            )}
            <div className="movie-info">
              <h3>{m.title}</h3>
              {m.duration_minutes && (
                <p className="muted">{m.duration_minutes} min</p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
