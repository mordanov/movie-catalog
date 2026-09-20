import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Reset location mock
Object.defineProperty(window, "location", {
  value: { href: "" },
  writable: true,
});

describe("api.media.list", () => {
  beforeEach(() => { mockFetch.mockReset(); });

  it("builds correct URL with no params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    const { api } = await import("./api");
    await api.media.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/media", expect.any(Object));
  });

  it("appends query params correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    const { api } = await import("./api");
    await api.media.list({ page: 2, category: "cartoon" });
    const url = (mockFetch.mock.calls[0][0] as string);
    expect(url).toContain("page=2");
    expect(url).toContain("category=cartoon");
  });

  it("redirects to /login on 401", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
    const { api } = await import("./api");
    await expect(api.media.list()).rejects.toThrow("Unauthorized");
    expect(window.location.href).toBe("/login");
  });
});
