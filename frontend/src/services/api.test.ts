import { describe, expect, it } from "vitest";
import { resolveApiBase } from "./api";

describe("resolveApiBase", () => {
  it("appends /api exactly once", () => {
    expect(resolveApiBase("http://localhost:8000")).toBe("http://localhost:8000/api");
    expect(resolveApiBase("http://localhost:8000/")).toBe("http://localhost:8000/api");
    expect(resolveApiBase("http://localhost:8000/api")).toBe("http://localhost:8000/api");
    expect(resolveApiBase("http://localhost:8000/api/")).toBe("http://localhost:8000/api");
  });
  it("falls back to the local backend when unset or blank", () => {
    expect(resolveApiBase(undefined)).toBe("http://localhost:8000/api");
    expect(resolveApiBase("")).toBe("http://localhost:8000/api");
    expect(resolveApiBase("   ")).toBe("http://localhost:8000/api");
  });
  it("supports a deployed backend and a same-origin proxy", () => {
    expect(resolveApiBase("https://my-api.onrender.com")).toBe("https://my-api.onrender.com/api");
    expect(resolveApiBase("/")).toBe("/api");
  });
});
