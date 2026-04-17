import { describe, it, expect } from "vitest";
import { apiClient, API_BASE_URL } from "../src/api/client";

describe("apiClient", () => {
  it("uses default base URL when VITE_API_BASE_URL is unset", () => {
    expect(typeof API_BASE_URL).toBe("string");
    expect(API_BASE_URL.length).toBeGreaterThan(0);
  });

  it("axios instance has matching baseURL", () => {
    expect(apiClient.defaults.baseURL).toBe(API_BASE_URL);
  });

  it("sends JSON by default", () => {
    expect(apiClient.defaults.headers["Content-Type"]).toBe("application/json");
  });
});
