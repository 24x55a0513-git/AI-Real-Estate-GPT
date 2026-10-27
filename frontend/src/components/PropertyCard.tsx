import { Link } from "react-router-dom";
import { Bath, BedDouble, Heart, Maximize2, MapPin, Scale, Car } from "lucide-react";
import type { Property } from "@/types";
import { Badge, Card } from "@/components/ui";
import { PropertyImage } from "@/components/PropertyImage";
import { useFavorites } from "@/hooks/useFavorites";
import { useCompare } from "@/hooks/useCompare";
import { FURNISHING_LABEL, PROPERTY_TYPE_LABEL, formatPrice } from "@/utils/format";
import { cn } from "@/utils/cn";

export function PropertyCard({ property: p, reasons }: { property: Property; reasons?: string[] }) {
  const fav = useFavorites();
  const compare = useCompare();
  const saved = fav.isFavorite(p.id);
  const inCompare = compare.has(p.id);

  return (
    <Card className="group overflow-hidden transition-shadow hover:shadow-xl">
      <div className="relative aspect-[4/3] overflow-hidden bg-charcoal-100">
        <Link to={`/properties/${p.id}`} aria-label={`View ${p.title}`}>
          <PropertyImage src={p.images[0]?.url} alt={p.images[0]?.alt ?? p.title} className="transition-transform duration-500 group-hover:scale-105" />
        </Link>
        <div className="absolute left-3 top-3 flex gap-1.5">
          <Badge tone="dark">{p.listing_type === "rent" ? "For Rent" : "For Sale"}</Badge>
          {p.is_demo && <Badge tone="gold" className="bg-white/90">Demo listing</Badge>}
        </div>
        <button onClick={() => fav.toggle(p.id)} disabled={fav.pending} aria-pressed={saved}
          aria-label={saved ? `Remove ${p.title} from favorites` : `Save ${p.title} to favorites`}
          className="absolute right-3 top-3 rounded-full bg-white/90 p-2 shadow transition hover:bg-white">
          <Heart className={cn("h-4 w-4", saved ? "fill-red-500 text-red-500" : "text-charcoal-700")} />
        </button>
      </div>
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="font-serif text-2xl font-semibold text-charcoal-900">{formatPrice(p.price, p.listing_type)}</p>
          <Badge>{PROPERTY_TYPE_LABEL[p.property_type]}</Badge>
        </div>
        <div>
          <Link to={`/properties/${p.id}`} className="line-clamp-1 font-medium hover:text-gold-600">{p.title}</Link>
          <p className="mt-0.5 flex items-center gap-1 text-sm text-charcoal-500"><MapPin className="h-3.5 w-3.5" />{p.locality}, {p.city}</p>
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-charcoal-600">
          {p.bedrooms > 0 && <li className="flex items-center gap-1"><BedDouble className="h-4 w-4" />{p.bedrooms} bd</li>}
          {p.bathrooms > 0 && <li className="flex items-center gap-1"><Bath className="h-4 w-4" />{p.bathrooms} ba</li>}
          <li className="flex items-center gap-1"><Maximize2 className="h-4 w-4" />{p.area_sqft.toLocaleString("en-IN")} sq ft</li>
          {p.has_parking && <li className="flex items-center gap-1"><Car className="h-4 w-4" />Parking</li>}
          {p.furnishing && <li>{FURNISHING_LABEL[p.furnishing]}</li>}
        </ul>
        {reasons && reasons.length > 0 && (
          <div className="rounded-xl bg-warm-200/70 p-3">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gold-700">Why this matches</p>
            <ul className="space-y-0.5 text-xs text-charcoal-700">{reasons.map((r) => <li key={r}>• {r}</li>)}</ul>
          </div>
        )}
        <button onClick={() => compare.toggle(p.id)} aria-pressed={inCompare}
          className={cn("flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
            inCompare ? "border-gold-500 bg-gold-300/30 text-gold-700" : "border-charcoal-200 text-charcoal-700 hover:bg-warm-200")}>
          <Scale className="h-4 w-4" />{inCompare ? "Added to compare" : "Add to compare"}
        </button>
      </div>
    </Card>
  );
}

export function PropertyCardSkeleton() {
  return (
    <Card className="overflow-hidden" >
      <div className="aspect-[4/3] animate-pulse bg-charcoal-100" />
      <div className="space-y-3 p-4">
        <div className="h-7 w-1/2 animate-pulse rounded bg-charcoal-100" />
        <div className="h-4 w-3/4 animate-pulse rounded bg-charcoal-100" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-charcoal-100" />
      </div>
    </Card>
  );
}
