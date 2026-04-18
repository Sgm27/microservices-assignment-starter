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
            (err as { message?: string })?.message ?? "Không tải được danh sách phim",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <p>Đang tải phim…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <div className="hero">
        <h1>Đang chiếu</h1>
        <p>Chọn phim và đặt vé trong vài giây.</p>
      </div>
      {movies.length === 0 ? (
        <p className="muted">Chưa có phim nào.</p>
      ) : (
        <div className="movie-grid">
          {movies.map((m) => (
            <Link key={m.id} to={`/movies/${m.id}`} className="movie-card">
              <MoviePoster src={m.poster_url} title={m.title} />
              <div className="movie-info">
                <h3>{m.title}</h3>
                <p className="muted">
                  {m.duration_minutes ? `${m.duration_minutes} phút` : ""}
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
