import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { ListingType, PropertyType, SearchParams } from "@/types";
import { Button, Field, Input, Select } from "@/components/ui";
import { PROPERTY_TYPES, PROPERTY_TYPE_LABEL, toNumber } from "@/utils/format";
import { cn } from "@/utils/cn";

const str = (n?: number) => (n === undefined ? "" : String(n));

/** Local draft of the filters; "Apply" pushes it to the URL (which drives the backend query). */
export function FilterPanel({ value, onApply, onClear }: { value: SearchParams; onApply: (v: SearchParams) => void; onClear: () => void }) {
  const facets = useQuery({ queryKey: ["facets"], queryFn: api.properties.facets, staleTime: 5 * 60_000 });
  const [d, setD] = useState<SearchParams>(value);
  useEffect(() => setD(value), [value]);

  const set = <K extends keyof SearchParams>(k: K, v: SearchParams[K]) => setD((cur) => ({ ...cur, [k]: v }));
  const toggleIn = <T extends string>(list: T[] | undefined, item: T): T[] => {
    const cur = list ?? [];
    return cur.includes(item) ? cur.filter((x) => x !== item) : [...cur, item];
  };
  const cities = facets.data?.cities ?? [];
  const localities = d.city ? facets.data?.localities[d.city] ?? [] : [];

  return (
    <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); onApply({ ...d, page: 1 }); }} aria-label="Property filters">
      <div className="grid grid-cols-2 gap-1 rounded-xl bg-charcoal-100 p-1" role="group" aria-label="Buy or rent">
        {([["", "All"], ["buy", "Buy"], ["rent", "Rent"]] as [string, string][]).slice(1).map(([v, label]) => (
          <button key={v} type="button" aria-pressed={d.listing_type === v}
            onClick={() => set("listing_type", d.listing_type === v ? undefined : (v as ListingType))}
            className={cn("rounded-lg py-2 text-sm font-medium transition", d.listing_type === v ? "bg-charcoal-900 text-warm-50" : "text-charcoal-600 hover:bg-white")}>{label}</button>
        ))}
      </div>

      <Field label="City" htmlFor="f-city">
        <Select id="f-city" value={d.city ?? ""} onChange={(e) => setD((c) => ({ ...c, city: e.target.value || undefined, locality: undefined }))}>
          <option value="">All cities</option>
          {cities.map((c) => <option key={c}>{c}</option>)}
        </Select>
      </Field>
      <Field label="Locality" htmlFor="f-locality">
        <Input id="f-locality" list="locality-options" placeholder="e.g. Gachibowli" value={d.locality ?? ""} onChange={(e) => set("locality", e.target.value || undefined)} />
        <datalist id="locality-options">{localities.map((l) => <option key={l} value={l} />)}</datalist>
      </Field>

      <fieldset>
        <legend className="mb-1.5 text-sm font-medium">Property type</legend>
        <div className="flex flex-wrap gap-2">
          {PROPERTY_TYPES.map((t: PropertyType) => {
            const on = d.property_type?.includes(t);
            return <button key={t} type="button" aria-pressed={on} onClick={() => set("property_type", toggleIn(d.property_type, t))}
              className={cn("rounded-full border px-3 py-1 text-xs font-medium transition", on ? "border-gold-500 bg-gold-300/30 text-gold-700" : "border-charcoal-200 hover:bg-warm-200")}>{PROPERTY_TYPE_LABEL[t]}</button>;
          })}
        </div>
      </fieldset>

      <div className="grid grid-cols-2 gap-3">
        <Field label={d.listing_type === "rent" ? "Min rent (₹/mo)" : "Min price (₹)"} htmlFor="f-minp">
          <Input id="f-minp" inputMode="numeric" min={0} placeholder="0" value={str(d.min_price)} onChange={(e) => set("min_price", toNumber(e.target.value))} />
        </Field>
        <Field label={d.listing_type === "rent" ? "Max rent (₹/mo)" : "Max price (₹)"} htmlFor="f-maxp">
          <Input id="f-maxp" inputMode="numeric" min={0} placeholder="Any" value={str(d.max_price)} onChange={(e) => set("max_price", toNumber(e.target.value))} />
        </Field>
        <Field label="Bedrooms (min)" htmlFor="f-bed">
          <Select id="f-bed" value={str(d.bedrooms)} onChange={(e) => set("bedrooms", toNumber(e.target.value))}>
            <option value="">Any</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}+</option>)}
          </Select>
        </Field>
        <Field label="Bathrooms (min)" htmlFor="f-bath">
          <Select id="f-bath" value={str(d.bathrooms)} onChange={(e) => set("bathrooms", toNumber(e.target.value))}>
            <option value="">Any</option>{[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}+</option>)}
          </Select>
        </Field>
        <Field label="Min area (sq ft)" htmlFor="f-mina"><Input id="f-mina" inputMode="numeric" value={str(d.min_area)} onChange={(e) => set("min_area", toNumber(e.target.value))} /></Field>
        <Field label="Max area (sq ft)" htmlFor="f-maxa"><Input id="f-maxa" inputMode="numeric" value={str(d.max_area)} onChange={(e) => set("max_area", toNumber(e.target.value))} /></Field>
      </div>

      <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-gold-500" checked={!!d.has_parking} onChange={(e) => set("has_parking", e.target.checked || undefined)} />Parking available</label>

      {(facets.data?.amenities.length ?? 0) > 0 && (
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">Amenities</legend>
          <div className="grid grid-cols-1 gap-1.5">
            {facets.data!.amenities.map((a) => (
              <label key={a} className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="h-4 w-4 accent-gold-500" checked={d.amenity?.includes(a) ?? false} onChange={() => set("amenity", toggleIn(d.amenity, a))} />{a}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="flex gap-2 pt-1">
        <Button type="submit" variant="gold" className="flex-1">Apply filters</Button>
        <Button type="button" variant="outline" onClick={onClear}>Clear</Button>
      </div>
    </form>
  );
}
