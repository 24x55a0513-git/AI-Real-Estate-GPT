import type { Furnishing, ListingType, PropertyType } from "@/types";

/** ₹25,000/mo for rent; ₹58 Lakh / ₹1.5 Cr for sale. */
export function formatPrice(price: number, listing: ListingType): string {
  if (listing === "rent") return `₹${Math.round(price).toLocaleString("en-IN")}/mo`;
  if (price >= 1e7) return `₹${trim(price / 1e7)} Cr`;
  if (price >= 1e5) return `₹${trim(price / 1e5)} Lakh`;
  return `₹${Math.round(price).toLocaleString("en-IN")}`;
}
const trim = (n: number) => String(Number(n.toFixed(2)));

export const formatInr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

/** Price per sq ft, or null when the area is missing/zero. */
export function pricePerSqft(price: number, area: number | null | undefined): number | null {
  return area && area > 0 ? Math.round((price / area) * 100) / 100 : null;
}

export const PROPERTY_TYPE_LABEL: Record<PropertyType, string> = {
  apartment: "Apartment", independent_house: "Independent House", villa: "Villa", plot: "Plot", commercial: "Commercial",
};
export const FURNISHING_LABEL: Record<Furnishing, string> = {
  furnished: "Furnished", semi_furnished: "Semi-furnished", unfurnished: "Unfurnished",
};
export const PROPERTY_TYPES = Object.keys(PROPERTY_TYPE_LABEL) as PropertyType[];

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

/** Parse "1.5", "60" style numeric form input into a finite number or undefined. */
export function toNumber(v: string | null | undefined): number | undefined {
  if (v === null || v === undefined || v.trim() === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : undefined;
}
