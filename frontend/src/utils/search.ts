import type { ListingType, PropertyType, SearchParams } from "@/types";
import { PROPERTY_TYPES, toNumber } from "@/utils/format";

/** Filters live in the URL (shareable, survives refresh) and are translated to/from API params here. */
export function paramsFromURL(sp: URLSearchParams): SearchParams {
  const lt = sp.get("listing_type");
  const sort = sp.get("sort");
  return {
    city: sp.get("city") || undefined, locality: sp.get("locality") || undefined, q: sp.get("q") || undefined,
    listing_type: lt === "buy" || lt === "rent" ? (lt as ListingType) : undefined,
    property_type: sp.getAll("property_type").filter((t): t is PropertyType => (PROPERTY_TYPES as string[]).includes(t)),
    min_price: toNumber(sp.get("min_price")), max_price: toNumber(sp.get("max_price")),
    bedrooms: toNumber(sp.get("bedrooms")), bathrooms: toNumber(sp.get("bathrooms")),
    min_area: toNumber(sp.get("min_area")), max_area: toNumber(sp.get("max_area")),
    amenity: sp.getAll("amenity"), has_parking: sp.get("has_parking") === "true" ? true : undefined,
    sort: sort === "price_asc" || sort === "price_desc" ? sort : "newest",
    page: Math.max(1, toNumber(sp.get("page")) ?? 1), page_size: 12,
  };
}

export function paramsToURL(p: SearchParams): URLSearchParams {
  const sp = new URLSearchParams();
  const put = (k: string, v: unknown) => { if (v !== undefined && v !== null && v !== "") sp.set(k, String(v)); };
  put("city", p.city); put("locality", p.locality); put("q", p.q); put("listing_type", p.listing_type);
  p.property_type?.forEach((t) => sp.append("property_type", t));
  put("min_price", p.min_price); put("max_price", p.max_price); put("bedrooms", p.bedrooms); put("bathrooms", p.bathrooms);
  put("min_area", p.min_area); put("max_area", p.max_area);
  p.amenity?.forEach((a) => sp.append("amenity", a));
  if (p.has_parking) sp.set("has_parking", "true");
  if (p.sort && p.sort !== "newest") sp.set("sort", p.sort);
  if (p.page && p.page > 1) sp.set("page", String(p.page));
  return sp;
}
