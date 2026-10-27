import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SlidersHorizontal, Search } from "lucide-react";
import { api } from "@/services/api";
import type { SearchParams } from "@/types";
import { Button, DemoNotice, EmptyState, ErrorState, Input, PageHeader, Select } from "@/components/ui";
import { FilterPanel } from "@/components/FilterPanel";
import { Pagination } from "@/components/Pagination";
import { PropertyCard, PropertyCardSkeleton } from "@/components/PropertyCard";
import { paramsFromURL, paramsToURL } from "@/utils/search";

export default function Explore() {
  const [sp, setSp] = useSearchParams();
  const params = useMemo(() => paramsFromURL(sp), [sp]);
  const [showFilters, setShowFilters] = useState(false);
  const [q, setQ] = useState(params.q ?? "");

  const query = useQuery({ queryKey: ["properties", params], queryFn: () => api.properties.list(params), placeholderData: keepPreviousData });
  const apply = (next: SearchParams) => { setSp(paramsToURL(next)); setShowFilters(false); window.scrollTo({ top: 0 }); };
  const clear = () => { setQ(""); setSp(new URLSearchParams()); };
  const hasFilters = sp.toString().replace(/(^|&)(page|sort)=[^&]*/g, "") !== "";
  const data = query.data;

  return (
    <div className="container-page py-10">
      <PageHeader title="Explore properties" subtitle="Filters run against the database. Your search is saved in the page URL, so you can refresh or share it." />
      <form className="mb-6 flex flex-col gap-3 sm:flex-row" onSubmit={(e) => { e.preventDefault(); apply({ ...params, q: q.trim() || undefined, page: 1 }); }} role="search">
        <div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-charcoal-400" />
          <Input aria-label="Keyword search" className="pl-9" placeholder="Search by keyword, locality or city…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Select aria-label="Sort results" className="sm:w-52" value={params.sort} onChange={(e) => apply({ ...params, sort: e.target.value as SearchParams["sort"], page: 1 })}>
          <option value="newest">Newest first</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option>
        </Select>
        <Button type="submit" variant="gold">Search</Button>
        <Button type="button" variant="outline" className="lg:hidden" onClick={() => setShowFilters(!showFilters)}><SlidersHorizontal className="h-4 w-4" />Filters</Button>
      </form>

      <div className="grid gap-8 lg:grid-cols-[18rem_1fr]">
        <aside className={`${showFilters ? "block" : "hidden"} h-fit rounded-2xl border border-charcoal-100 bg-white p-5 shadow-card lg:sticky lg:top-24 lg:block`}>
          <FilterPanel value={params} onApply={apply} onClear={clear} />
        </aside>
        <section aria-live="polite">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-charcoal-600">{query.isLoading ? "Searching…" : data ? <><strong>{data.total.toLocaleString("en-IN")}</strong> {data.total === 1 ? "property" : "properties"} found</> : null}</p>
            {hasFilters && <Button variant="ghost" size="sm" onClick={clear}>Clear all filters</Button>}
          </div>
          {query.isError ? <ErrorState message={(query.error as Error).message} onRetry={() => query.refetch()} /> :
            query.isLoading ? <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <PropertyCardSkeleton key={i} />)}</div> :
            data && data.items.length === 0 ? <EmptyState title="No properties match your filters" message="Try widening your budget, removing a filter, or searching another city." action={<Button variant="gold" onClick={clear}>Clear filters</Button>} /> : (
              <>
                <div className={`grid gap-6 sm:grid-cols-2 xl:grid-cols-3 ${query.isFetching ? "opacity-60" : ""}`}>{data?.items.map((p) => <PropertyCard key={p.id} property={p} />)}</div>
                <Pagination page={data?.page ?? 1} totalPages={data?.total_pages ?? 1} onChange={(page) => apply({ ...params, page })} />
              </>
            )}
          <div className="mt-8"><DemoNotice /></div>
        </section>
      </div>
    </div>
  );
}
