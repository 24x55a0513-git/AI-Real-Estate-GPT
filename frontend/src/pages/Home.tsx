import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Building, Building2, Home as HomeIcon, Landmark, MapPin, Search, ShieldCheck, Sparkles, Trees, Wallet } from "lucide-react";
import { api } from "@/services/api";
import type { ListingType, PropertyType } from "@/types";
import { Button, DemoNotice, ErrorState, Field, Input, Select } from "@/components/ui";
import { PropertyCard, PropertyCardSkeleton } from "@/components/PropertyCard";
import { PROPERTY_TYPE_LABEL, toNumber } from "@/utils/format";
import { cn } from "@/utils/cn";

const CATEGORY_ICONS: Record<PropertyType, typeof Building> = {
  apartment: Building2, independent_house: HomeIcon, villa: Landmark, plot: Trees, commercial: Building,
};
const SAMPLE_PROMPTS = [
  "Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking",
  "Show villas in Bengaluru between ₹80 lakh and ₹1.5 crore",
  "Find a rental flat in Hyderabad under ₹25,000 per month",
];

export default function Home() {
  const navigate = useNavigate();
  const [listing, setListing] = useState<ListingType>("buy");
  const [city, setCity] = useState("");
  const [location, setLocation] = useState("");
  const [budget, setBudget] = useState("");

  const facets = useQuery({ queryKey: ["facets"], queryFn: api.properties.facets, staleTime: 5 * 60_000 });
  const featured = useQuery({ queryKey: ["featured"], queryFn: () => api.properties.list({ page_size: 6, sort: "newest" }) });

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const sp = new URLSearchParams({ listing_type: listing });
    if (city) sp.set("city", city);
    if (location.trim()) sp.set("locality", location.trim());
    const max = toNumber(budget);
    if (max) sp.set("max_price", String(max));
    navigate(`/explore?${sp.toString()}`);
  };

  return (
    <>
      <section className="relative overflow-hidden bg-charcoal-900 text-warm-50">
        <div className="absolute inset-0 opacity-25" style={{ backgroundImage: "url(https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1800&q=70)", backgroundSize: "cover", backgroundPosition: "center" }} aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-b from-charcoal-950/70 to-charcoal-900" aria-hidden />
        <div className="container-page relative py-20 sm:py-28">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-gold-500/40 px-3 py-1 text-xs font-medium text-gold-300"><Sparkles className="h-3.5 w-3.5" />Conversational property search</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-6xl">Find Your Place. <span className="text-gold-400">Let AI Do the Searching.</span></h1>
          <p className="mt-5 max-w-xl text-lg text-charcoal-200">Discover homes that fit your lifestyle and budget with an intelligent property search experience.</p>

          <form onSubmit={onSearch} className="mt-10 max-w-4xl rounded-2xl bg-white p-4 text-charcoal-900 shadow-2xl sm:p-5" aria-label="Search properties">
            <div className="mb-4 inline-flex rounded-xl bg-charcoal-100 p-1" role="group" aria-label="Buy or rent">
              {(["buy", "rent"] as ListingType[]).map((t) => (
                <button key={t} type="button" aria-pressed={listing === t} onClick={() => setListing(t)}
                  className={cn("rounded-lg px-6 py-2 text-sm font-medium capitalize transition", listing === t ? "bg-charcoal-900 text-warm-50" : "text-charcoal-600")}>{t}</button>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
              <Field label="City" htmlFor="h-city">
                <Select id="h-city" value={city} onChange={(e) => setCity(e.target.value)}>
                  <option value="">Any city</option>{(facets.data?.cities ?? []).map((c) => <option key={c}>{c}</option>)}
                </Select>
              </Field>
              <Field label="Locality" htmlFor="h-loc"><Input id="h-loc" placeholder="e.g. Whitefield" value={location} onChange={(e) => setLocation(e.target.value)} /></Field>
              <Field label={listing === "rent" ? "Max rent (₹/month)" : "Max budget (₹)"} htmlFor="h-budget">
                <Input id="h-budget" inputMode="numeric" placeholder={listing === "rent" ? "e.g. 30000" : "e.g. 7500000"} value={budget} onChange={(e) => setBudget(e.target.value)} />
              </Field>
              <Button type="submit" variant="gold" size="lg"><Search className="h-4 w-4" />Search</Button>
            </div>
          </form>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button variant="gold" size="lg" onClick={() => navigate("/explore")}>Explore properties<ArrowRight className="h-4 w-4" /></Button>
            <Button variant="outline" size="lg" className="border-white/30 bg-transparent text-warm-50 hover:bg-white/10" onClick={() => navigate("/assistant")}><Sparkles className="h-4 w-4" />Ask the assistant</Button>
          </div>
        </div>
      </section>

      <section className="container-page py-16">
        <div className="mb-8 flex items-end justify-between"><div><h2 className="text-3xl font-semibold">Featured properties</h2><p className="mt-2 text-charcoal-500">The newest demo listings in our database.</p></div>
          <Link to="/explore" className="hidden text-sm font-medium text-gold-600 hover:underline sm:block">View all →</Link></div>
        {featured.isError ? <ErrorState message={(featured.error as Error).message} onRetry={() => featured.refetch()} /> : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {featured.isLoading ? Array.from({ length: 3 }, (_, i) => <PropertyCardSkeleton key={i} />) : featured.data?.items.map((p) => <PropertyCard key={p.id} property={p} />)}
          </div>
        )}
        <div className="mt-6"><DemoNotice /></div>
      </section>

      <section className="bg-warm-200/60 py-16">
        <div className="container-page">
          <h2 className="text-3xl font-semibold">Popular cities</h2>
          <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            {(facets.data?.cities ?? ["Hyderabad", "Bengaluru", "Chennai", "Pune"]).map((c) => (
              <Link key={c} to={`/explore?city=${encodeURIComponent(c)}`} className="group rounded-2xl bg-charcoal-900 p-6 text-warm-50 transition hover:bg-charcoal-800">
                <MapPin className="mb-6 h-6 w-6 text-gold-400" /><p className="font-serif text-2xl">{c}</p>
                <p className="mt-1 flex items-center gap-1 text-sm text-charcoal-200">Browse listings <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-1" /></p>
              </Link>
            ))}
          </div>
          <h2 className="mt-14 text-3xl font-semibold">Browse by category</h2>
          <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-5">
            {(Object.keys(PROPERTY_TYPE_LABEL) as PropertyType[]).map((t) => {
              const Icon = CATEGORY_ICONS[t];
              return <Link key={t} to={`/explore?property_type=${t}`} className="flex flex-col items-center gap-3 rounded-2xl border border-charcoal-100 bg-white p-6 text-center shadow-card transition hover:-translate-y-0.5">
                <Icon className="h-7 w-7 text-gold-600" /><span className="text-sm font-medium">{PROPERTY_TYPE_LABEL[t]}</span></Link>;
            })}
          </div>
        </div>
      </section>

      <section className="container-page py-16">
        <h2 className="text-3xl font-semibold">How it works</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3">
          {[["Describe or filter", "Type what you need in plain English, or use detailed filters."], ["We query the database", "Your request becomes structured filters that run against real stored records."], ["Review, compare, save", "See why each result matches, compare up to four, and save favorites."]].map(([t, d], i) => (
            <li key={t} className="rounded-2xl border border-charcoal-100 bg-white p-6 shadow-card"><span className="font-serif text-4xl text-gold-500">0{i + 1}</span><h3 className="mt-3 text-xl font-semibold">{t}</h3><p className="mt-2 text-sm text-charcoal-500">{d}</p></li>
          ))}
        </ol>
      </section>

      <section className="bg-charcoal-900 py-16 text-warm-50">
        <div className="container-page grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="mb-3 flex items-center gap-2 text-sm font-medium text-gold-300"><Sparkles className="h-4 w-4" />Meet Real Estate GPT</p>
            <h2 className="text-3xl font-semibold sm:text-4xl">Just say what you’re looking for</h2>
            <p className="mt-4 text-charcoal-200">The assistant understands Indian budgets like “60 lakh” or “1.5 crore”, bedrooms, property types, and buy vs. rent, then returns matching records with the reasons they fit. It uses transparent rule-based parsing, not a large language model, and never invents listings.</p>
            <Button variant="gold" size="lg" className="mt-6" onClick={() => navigate("/assistant")}>Open the assistant<ArrowRight className="h-4 w-4" /></Button>
          </div>
          <div className="space-y-3">
            {SAMPLE_PROMPTS.map((p) => (
              <Link key={p} to={`/assistant?q=${encodeURIComponent(p)}`} className="block rounded-xl border border-white/10 bg-white/5 p-4 text-sm transition hover:border-gold-500/60 hover:bg-white/10">“{p}”</Link>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-16">
        <h2 className="text-3xl font-semibold">Why Real Estate GPT</h2>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {[[Search, "Transparent search", "Every result comes from the database, with the reasons it matches."], [Wallet, "Indian-currency aware", "Understands lakh, crore, thousand and monthly rent."], [ShieldCheck, "Secure by design", "Hashed passwords, expiring tokens and server-side permissions."]].map(([I, t, d]) => {
            const Icon = I as typeof Search;
            return <div key={t as string} className="rounded-2xl border border-charcoal-100 bg-white p-6 shadow-card"><Icon className="h-6 w-6 text-gold-600" /><h3 className="mt-3 text-lg font-semibold">{t as string}</h3><p className="mt-1 text-sm text-charcoal-500">{d as string}</p></div>;
          })}
        </div>
        <div className="mt-12 rounded-3xl bg-gold-500 p-10 text-center text-charcoal-950">
          <h2 className="text-3xl font-semibold">Ready to find your place?</h2>
          <p className="mx-auto mt-2 max-w-lg">Start with a search, or ask the assistant in plain English.</p>
          <div className="mt-6 flex justify-center gap-3"><Button onClick={() => navigate("/explore")}>Explore properties</Button><Button variant="outline" onClick={() => navigate("/register")}>Create free account</Button></div>
        </div>
      </section>
    </>
  );
}
