import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

vi.mock("../src/api/movies", () => ({
  listMovies: () => Promise.resolve([]),
  getMovie: () => Promise.resolve(null),
  getShowtime: () => Promise.resolve(null),
  getShowtimeSeats: () => Promise.resolve([]),
}));

describe("App", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(screen.getByText(/Cinema/i)).toBeInTheDocument();
  });
});
