import { useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building, Home as HomeIcon, Inbox, KeyRound, Pencil, Plus, Trash2, Users } from "lucide-react";
import { api, ApiError } from "@/services/api";
import type { Inquiry, Property, PropertyStatus } from "@/types";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Input, PageHeader, Select, Skeleton } from "@/components/ui";
import { Pagination } from "@/components/Pagination";
import { useToast } from "@/hooks/useToast";
import { formatDate, formatPrice } from "@/utils/format";
import { cn } from "@/utils/cn";

export default function AdminDashboard() {
  const qc = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState<"properties" | "inquiries">("properties");
  const [status, setStatus] = useState<"" | PropertyStatus>("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [toDelete, setToDelete] = useState<Property | null>(null);

  const stats = useQuery({ queryKey: ["admin", "stats"], queryFn: api.admin.stats });
  const props = useQuery({ queryKey: ["admin", "properties", status, q, page], placeholderData: keepPreviousData,
    queryFn: () => api.admin.properties({ status: status || undefined, q: q.trim() || undefined, page, page_size: 10, sort: "newest" }) });
  const inquiries = useQuery({ queryKey: ["admin", "inquiries"], queryFn: () => api.admin.inquiries(), enabled: tab === "inquiries" });

  const refresh = () => { qc.invalidateQueries({ queryKey: ["admin"] }); qc.invalidateQueries({ queryKey: ["properties"] }); qc.invalidateQueries({ queryKey: ["featured"] }); };
  const err = (e: unknown) => toast.error(e instanceof ApiError ? e.message : "Action failed");
  const setPropStatus = useMutation({ mutationFn: (v: { id: number; s: PropertyStatus }) => api.admin.setStatus(v.id, v.s), onSuccess: () => { refresh(); toast.success("Status updated"); }, onError: err });
  const remove = useMutation({ mutationFn: (id: number) => api.admin.remove(id), onSuccess: () => { refresh(); setToDelete(null); toast.success("Property deleted"); }, onError: err });
  const setInqStatus = useMutation({ mutationFn: (v: { id: number; s: Inquiry["status"] }) => api.admin.setInquiryStatus(v.id, v.s),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin"] }); toast.success("Inquiry updated"); }, onError: err });

  const s = stats.data;
  const cards = [
    { label: "Total properties", value: s?.total_properties, icon: Building }, { label: "For sale (active)", value: s?.sale_listings, icon: HomeIcon },
    { label: "For rent (active)", value: s?.rental_listings, icon: KeyRound }, { label: "Registered users", value: s?.total_users, icon: Users },
    { label: "New inquiries", value: s?.new_inquiries, icon: Inbox },
  ];

  return (
    <div className="container-page py-10">
      <PageHeader title="Admin dashboard" subtitle="Manage listings and inquiries. Every action is re-checked by the server."
        actions={<Link to="/admin/properties/new"><Button variant="gold"><Plus className="h-4 w-4" />Add property</Button></Link>} />
      {stats.isError && <ErrorState message={(stats.error as Error).message} onRetry={() => stats.refetch()} />}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {cards.map((c) => <Card key={c.label} className="p-4"><c.icon className="h-5 w-5 text-gold-600" />{stats.isLoading ? <Skeleton className="mt-2 h-8 w-12" /> : <p className="mt-1 font-serif text-3xl font-semibold">{c.value ?? "–"}</p>}<p className="text-xs text-charcoal-500">{c.label}</p></Card>)}
      </div>
      {s && <div className="mt-4 flex flex-wrap gap-2 text-xs">{Object.entries(s.by_city).map(([c, n]) => <Badge key={c}>{c}: {n}</Badge>)}<Badge tone="red">Inactive/sold/rented: {s.inactive_properties}</Badge></div>}

      <div className="mt-8 flex gap-2 border-b border-charcoal-200" role="tablist">
        {(["properties", "inquiries"] as const).map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
          className={cn("-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize", tab === t ? "border-gold-500 text-charcoal-900" : "border-transparent text-charcoal-500")}>{t}</button>)}
      </div>

      {tab === "properties" ? (
        <div className="mt-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row">
            <Input aria-label="Search properties" placeholder="Search title, city, locality…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
            <Select aria-label="Filter by status" className="sm:w-48" value={status} onChange={(e) => { setStatus(e.target.value as "" | PropertyStatus); setPage(1); }}>
              <option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="sold">Sold</option><option value="rented">Rented</option></Select>
          </div>
          {props.isError ? <ErrorState message={(props.error as Error).message} onRetry={() => props.refetch()} /> : props.isLoading ? <Skeleton className="h-64" /> :
            props.data?.items.length === 0 ? <EmptyState title="No properties found" /> : (
              <div className="overflow-x-auto rounded-2xl border border-charcoal-100 bg-white shadow-card">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-warm-200/60 text-xs uppercase tracking-wide text-charcoal-500"><tr><th className="p-3">Property</th><th className="p-3">Price</th><th className="p-3">Type</th><th className="p-3">Status</th><th className="p-3 text-right">Actions</th></tr></thead>
                  <tbody>{props.data?.items.map((p) => (
                    <tr key={p.id} className="border-t border-charcoal-100">
                      <td className="p-3"><Link to={`/properties/${p.id}`} className="font-medium hover:text-gold-600">{p.title}</Link><p className="text-xs text-charcoal-500">{p.locality}, {p.city} {p.is_demo && "· demo"}</p></td>
                      <td className="p-3">{formatPrice(p.price, p.listing_type)}</td>
                      <td className="p-3">{p.listing_type === "rent" ? "Rent" : "Sale"}</td>
                      <td className="p-3"><Select aria-label={`Status of ${p.title}`} className="h-9 w-32" value={p.status} onChange={(e) => setPropStatus.mutate({ id: p.id, s: e.target.value as PropertyStatus })}>
                        <option value="active">Active</option><option value="inactive">Inactive</option><option value="sold">Sold</option><option value="rented">Rented</option></Select></td>
                      <td className="p-3"><div className="flex justify-end gap-1">
                        <Link to={`/admin/properties/${p.id}/edit`} aria-label={`Edit ${p.title}`}><Button variant="ghost" size="sm"><Pencil className="h-4 w-4" /></Button></Link>
                        <Button variant="ghost" size="sm" aria-label={`Delete ${p.title}`} onClick={() => setToDelete(p)}><Trash2 className="h-4 w-4 text-red-600" /></Button></div></td>
                    </tr>))}</tbody>
                </table>
              </div>)}
          <Pagination page={props.data?.page ?? 1} totalPages={props.data?.total_pages ?? 1} onChange={setPage} />
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {inquiries.isError ? <ErrorState message={(inquiries.error as Error).message} onRetry={() => inquiries.refetch()} /> : inquiries.isLoading ? <Skeleton className="h-40" /> :
            inquiries.data?.length === 0 ? <EmptyState title="No inquiries yet" /> : inquiries.data?.map((i) => (
              <Card key={i.id} className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><p className="font-medium">{i.name} <span className="font-normal text-charcoal-500">· {i.email}{i.phone && ` · ${i.phone}`}</span></p>
                    <p className="text-xs text-charcoal-500">{i.property_title ? `About: ${i.property_title}` : "General inquiry"} · {formatDate(i.created_at)}</p></div>
                  <Select aria-label={`Status of inquiry ${i.id}`} className="h-9 w-36" value={i.status} onChange={(e) => setInqStatus.mutate({ id: i.id, s: e.target.value as Inquiry["status"] })}>
                    <option value="new">New</option><option value="contacted">Contacted</option><option value="closed">Closed</option></Select>
                </div>
                <p className="mt-3 whitespace-pre-line text-sm text-charcoal-700">{i.message}</p>
              </Card>))}
        </div>
      )}

      <ConfirmDialog open={!!toDelete} danger title="Delete this property?" loading={remove.isPending} confirmLabel="Delete permanently"
        message={`“${toDelete?.title ?? ""}” will be permanently removed, along with its favorites. To merely hide it, set its status to Inactive instead.`}
        onConfirm={() => toDelete && remove.mutate(toDelete.id)} onCancel={() => setToDelete(null)} />
    </div>
  );
}
