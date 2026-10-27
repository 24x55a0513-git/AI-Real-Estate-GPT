import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Trophy, X } from "lucide-react";
import { api } from "@/services/api";
import type { CompareResult, Property } from "@/types";
import { Badge, Button, EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { PropertyImage } from "@/components/PropertyImage";
import { useCompare } from "@/hooks/useCompare";
import { FURNISHING_LABEL, PROPERTY_TYPE_LABEL, formatInr, formatPrice } from "@/utils/format";
import { cn } from "@/utils/cn";

interface Row { key: string; label: string; render: (p: Property, r: CompareResult) => React.ReactNode }
const dash = <span className="text-charcoal-400">—</span>;

const ROWS: Row[] = [
  { key: "price", label: "Price", render: (p, r) => <span className="font-semibold">{formatPrice(p.price, p.listing_type)}{r.lowest_price_id === p.id && <Badge tone="green" className="ml-2">Lowest</Badge>}</span> },
  { key: "ppsf", label: "Price per sq ft", render: (p, r) => { const v = r.items.find((i) => i.property.id === p.id)?.price_per_sqft; return v == null ? dash : <span>{formatInr(v)}{r.lowest_price_per_sqft_id === p.id && <Badge tone="green" className="ml-2">Lowest</Badge>}</span>; } },
  { key: "city", label: "City", render: (p) => p.city },
  { key: "locality", label: "Locality", render: (p) => p.locality },
  { key: "property_type", label: "Type", render: (p) => PROPERTY_TYPE_LABEL[p.property_type] },
  { key: "listing_type", label: "Listing", render: (p) => (p.listing_type === "rent" ? "For rent" : "For sale") },
  { key: "area_sqft", label: "Area", render: (p, r) => <span>{p.area_sqft > 0 ? `${p.area_sqft.toLocaleString("en-IN")} sq ft` : "—"}{r.largest_area_id === p.id && <Badge tone="gold" className="ml-2">Largest</Badge>}</span> },
  { key: "bedrooms", label: "Bedrooms", render: (p) => p.bedrooms || dash },
  { key: "bathrooms", label: "Bathrooms", render: (p) => p.bathrooms || dash },
  { key: "has_parking", label: "Parking", render: (p) => (p.has_parking ? "Yes" : "No") },
  { key: "furnishing", label: "Furnishing", render: (p) => (p.furnishing ? FURNISHING_LABEL[p.furnishing] : dash) },
  { key: "amenities", label: "Amenities", render: (p) => (p.amenities.length ? p.amenities.join(", ") : dash) },
];

export default function Compare() {
  const compare = useCompare();
  const [sp, setSp] = useSearchParams();

  // Deep link (e.g. from the assistant): ?ids=1,2,3 seeds the compare list once.
  useEffect(() => {
    const raw = sp.get("ids");
    if (raw) {
      compare.set(raw.split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0));
      setSp({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ids = compare.ids;
  const q = useQuery({ queryKey: ["compare", ids], queryFn: () => api.properties.compare(ids), enabled: ids.length >= 2, retry: false });

  return (
    <div className="container-page py-10">
      <PageHeader title="Compare properties" subtitle="Compare two to four listings side by side. Differences are highlighted."
        actions={ids.length > 0 ? <Button variant="outline" onClick={compare.clear}>Clear all</Button> : undefined} />
      {ids.length < 2 ? (
        <EmptyState title={ids.length === 0 ? "Nothing to compare yet" : "Add one more property"} message="Use “Add to compare” on any property card (2 to 4 properties)."
          action={<Link to="/explore"><Button variant="gold">Browse properties</Button></Link>} />
      ) : q.isLoading ? <Skeleton className="h-96" /> : q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : q.data && (
        <>
          <div className="overflow-x-auto rounded-2xl border border-charcoal-100 bg-white shadow-card">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead><tr>
                <th scope="col" className="w-40 p-4" />
                {q.data.items.map(({ property: p }) => (
                  <th key={p.id} scope="col" className="p-4 align-top">
                    <div className="relative">
                      <button onClick={() => compare.remove(p.id)} aria-label={`Remove ${p.title} from comparison`} className="absolute right-1 top-1 z-10 rounded-full bg-white/90 p-1 shadow hover:bg-white"><X className="h-4 w-4" /></button>
                      <div className="aspect-[4/3] overflow-hidden rounded-xl bg-charcoal-100"><PropertyImage src={p.images[0]?.url} alt={p.title} /></div>
                      <Link to={`/properties/${p.id}`} className="mt-2 block font-serif text-base font-semibold hover:text-gold-600">{p.title}</Link>
                    </div>
                  </th>))}
              </tr></thead>
              <tbody>
                {ROWS.map((row) => {
                  const differs = row.key === "ppsf" || q.data!.differing_fields.includes(row.key);
                  return (
                    <tr key={row.key} className={cn("border-t border-charcoal-100", differs && "bg-gold-300/15")}>
                      <th scope="row" className="p-4 font-medium text-charcoal-600">{row.label}{differs && <span className="sr-only"> (differs)</span>}</th>
                      {q.data!.items.map(({ property: p }) => <td key={p.id} className="p-4">{row.render(p, q.data!)}</td>)}
                    </tr>);
                })}
              </tbody>
            </table>
          </div>
          <ul className="mt-4 space-y-1 text-xs text-charcoal-500">
            <li className="flex items-center gap-1"><Trophy className="h-3.5 w-3.5 text-gold-600" />Highlighted rows show where the listings differ.</li>
            {q.data.notes.map((n) => <li key={n}>• {n}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}
