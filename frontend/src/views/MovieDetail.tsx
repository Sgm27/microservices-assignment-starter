import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import { formatDateVi, formatVND } from "../utils/format";
import type { Movie } from "../types";

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
            (err as { message?: string })?.message ?? "Không tải được phim",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) return <p>Đang tải phim…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!movie) return <p>Không tìm thấy phim.</p>;

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
            <p className="muted">{movie.duration_minutes} phút</p>
          )}
          {movie.description && <p>{movie.description}</p>}
        </div>
      </div>

      <h2>Suất chiếu</h2>
      {showtimes.length === 0 ? (
        <p className="muted">Chưa có suất chiếu.</p>
      ) : (
        <ul className="showtime-list">
          {showtimes.map((s) => (
            <li key={s.id}>
              <Link
                to={`/showtimes/${s.id}/book`}
                className="showtime-card btn btn-ghost"
              >
                <span>{formatDateVi(s.starts_at)}</span>
                <span className="muted">Phòng {s.room}</span>
                <span>{formatVND(s.base_price)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
