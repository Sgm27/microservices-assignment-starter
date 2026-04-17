import apiClient from "./client";
import type { Movie, Seat, Showtime } from "../types";

export async function listMovies(): Promise<Movie[]> {
  const { data } = await apiClient.get<Movie[]>("/movies");
  return data;
}

export async function getMovie(id: string): Promise<Movie> {
  const { data } = await apiClient.get<Movie>(`/movies/${id}`);
  return data;
}

export async function getShowtime(id: string): Promise<Showtime> {
  const { data } = await apiClient.get<Showtime>(`/showtimes/${id}`);
  return data;
}

export async function getShowtimeSeats(id: string): Promise<Seat[]> {
  const { data } = await apiClient.get<Seat[]>(`/showtimes/${id}/seats`);
  return data;
}
