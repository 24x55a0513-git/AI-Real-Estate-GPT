import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bath, BedDouble, Car, Check, Heart, Mail, MapPin, Maximize2, Scale, Sofa } from "lucide-react";
import { api, ApiError } from "@/services/api";
import { Badge, Button, Card, DemoNotice, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { PropertyImage } from "@/components/PropertyImage";
import { useFavorites } from "@/hooks/useFavorites";
import { useCompare } from "@/hooks/useCompare";
import { FURNISHING_LABEL, PROPERTY_TYPE_LABEL, formatDate, formatInr, formatPrice, pricePerSqft } from "@/utils/format";
import { cn } from "@/utils/cn";

export default function PropertyDetails() {
  const { id } = useParams();
  const pid = Number(id);
  const valid = Number.isInteger(pid) && pid > 0;
  const q = useQuery({ queryKey: ["property", pid], queryFn: () => api.properties.get(pid), enabled: valid, retry: false });
  const fav = useFavorites();
  const compare = useCompare();
  const [active, setActive] = useState(0);

  if (!valid || (q.error instanceof ApiError && q.error.status === 404))
    return <div className="container-page py-16"><EmptyState title="Property not found" message="It may have been removed or is no longer available." action={<Link to="/explore"><Button variant="gold">Browse properties</Button></Link>} /></div>;
  if (q.isLoading) return <div className="container-page py-10"><Skeleton className="h-[420px]" /><Skeleton className="mt-6 h-40" /></div>;
  if (q.isError || !q.data) return <div className="container-page py-16"><ErrorState message={(q.error as Error)?.message ?? "Failed to load"} onRetry={() => q.refetch()} /></div>;

  const p = q.data;
  const ppsf = pricePerSqft(p.price, p.area_sqft);
  const images = p.images.length ? p.images : [{ id: 0, url: "", alt: p.title }];
  const saved = fav.isFavorite(p.id);
  const specs = [
    p.bedrooms > 0 && { icon: BedDouble, label: "Bedrooms", value: p.bedrooms },
    p.bathrooms > 0 && { icon: Bath, label: "Bathrooms", value: p.bathrooms },
    { icon: Maximize2, label: "Area", value: `${p.area_sqft.toLocaleString("en-IN")} sq ft` },
    { icon: Car, label: "Parking", value: p.has_parking ? "Available" : "Not listed" },
    p.furnishing && { icon: Sofa, label: "Furnishing", value: FURNISHING_LABEL[p.furnishing] },
  ].filter(Boolean) as { icon: typeof Bath; label: string; value: string | number }[];

  return (
    <div className="container-page py-8">
      <nav className="mb-4 text-sm text-charcoal-500" aria-label="Breadcrumb"><Link to="/explore" className="hover:text-gold-600">Explore</Link> / {p.city} / {p.locality}</nav>
      <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
        <div>
          <div className="aspect-[16/10] overflow-hidden rounded-2xl bg-charcoal-100"><PropertyImage src={images[active]?.url} alt={images[active]?.alt ?? p.title} className="" /></div>
          {images.length > 1 && <div className="mt-3 flex gap-3 overflow-x-auto">{images.map((im, i) => (
            <button key={im.id} onClick={() => setActive(i)} aria-label={`Show image ${i + 1}`} aria-current={i === active}
              className={cn("h-20 w-28 shrink-0 overflow-hidden rounded-lg border-2", i === active ? "border-gold-500" : "border-transparent opacity-70")}><PropertyImage src={im.url} alt="" /></button>))}</div>}

          <div className="mt-6 flex flex-wrap items-center gap-2"><Badge tone="dark">{p.listing_type === "rent" ? "For Rent" : "For Sale"}</Badge><Badge>{PROPERTY_TYPE_LABEL[p.property_type]}</Badge>
            {p.is_demo && <Badge tone="gold">Demo listing (fictional)</Badge>}{p.status !== "active" && <Badge tone="red">{p.status}</Badge>}</div>
          <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">{p.title}</h1>
          <p className="mt-2 flex items-center gap-1 text-charcoal-500"><MapPin className="h-4 w-4" />{p.address ?? `${p.locality}, ${p.city}`}</p>

          <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">{specs.map((s) => (
            <Card key={s.label} className="p-4"><s.icon className="h-5 w-5 text-gold-600" /><dt className="mt-2 text-xs uppercase tracking-wide text-charcoal-500">{s.label}</dt><dd className="font-semibold">{s.value}</dd></Card>))}</dl>

          <h2 className="mt-10 text-2xl font-semibold">About this property</h2>
          <p className="mt-3 whitespace-pre-line text-charcoal-700">{p.description}</p>
          {p.amenities.length > 0 && <><h2 className="mt-10 text-2xl font-semibold">Amenities</h2>
            <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">{p.amenities.map((a) => <li key={a} className="flex items-center gap-2 text-sm"><Check className="h-4 w-4 text-gold-600" />{a}</li>)}</ul></>}
          <p className="mt-8 text-xs text-charcoal-500">Listed {formatDate(p.created_at)} · Listing #{p.id}</p>
        </div>

        <aside className="h-fit space-y-4 lg:sticky lg:top-24">
          <Card className="p-6">
            <p className="font-serif text-4xl font-semibold">{formatPrice(p.price, p.listing_type)}</p>
            <p className="text-sm text-charcoal-500">{formatInr(p.price)}{p.listing_type === "rent" ? " per month" : ""}{ppsf !== null && <> · {formatInr(ppsf)}/sq ft</>}</p>
            <div className="mt-5 space-y-2">
              <Link to={`/contact?property=${p.id}`} className="block"><Button variant="gold" className="w-full"><Mail className="h-4 w-4" />Contact About This Property</Button></Link>
              <Button variant="outline" className="w-full" onClick={() => fav.toggle(p.id)} loading={fav.pending} aria-pressed={saved}><Heart className={cn("h-4 w-4", saved && "fill-red-500 text-red-500")} />{saved ? "Saved to favorites" : "Save to favorites"}</Button>
              <Button variant="outline" className="w-full" onClick={() => compare.toggle(p.id)} aria-pressed={compare.has(p.id)}><Scale className="h-4 w-4" />{compare.has(p.id) ? "Remove from compare" : "Add to compare"}</Button>
              {compare.ids.length >= 2 && <Link to="/compare" className="block text-center text-sm text-gold-600 hover:underline">Open comparison ({compare.ids.length})</Link>}
            </div>
          </Card>
          <DemoNotice />
        </aside>
      </div>
    </div>
  );
}
