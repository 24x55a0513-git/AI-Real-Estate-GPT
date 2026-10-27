import { describe, expect, it } from "vitest";
import { formatPrice, pricePerSqft, toNumber } from "./format";

describe("formatPrice", () => {
  it("formats sale prices in lakh and crore", () => {
    expect(formatPrice(6_000_000, "buy")).toBe("₹60 Lakh");
    expect(formatPrice(15_000_000, "buy")).toBe("₹1.5 Cr");
  });
  it("formats rent per month with Indian digit grouping", () => {
    expect(formatPrice(125_000, "rent")).toBe("₹1,25,000/mo");
  });
});

describe("pricePerSqft", () => {
  it("divides price by area", () => expect(pricePerSqft(5_800_000, 1150)).toBe(5043.48));
  it("is null for zero or missing area", () => {
    expect(pricePerSqft(1000, 0)).toBeNull();
    expect(pricePerSqft(1000, undefined)).toBeNull();
  });
});

describe("toNumber", () => {
  it("rejects blanks, negatives and junk", () => {
    expect(toNumber("")).toBeUndefined();
    expect(toNumber("-5")).toBeUndefined();
    expect(toNumber("abc")).toBeUndefined();
    expect(toNumber("12")).toBe(12);
  });
});
