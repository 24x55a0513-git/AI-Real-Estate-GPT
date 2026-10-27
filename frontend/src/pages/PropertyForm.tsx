import { useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, ApiError } from "@/services/api";
import type { Furnishing, ListingType, Property, PropertyInput, PropertyStatus, PropertyType } from "@/types";
import { Button, Card, ErrorState, Field, Input, PageHeader, Select, Skeleton, Textarea } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { FURNISHING_LABEL, PROPERTY_TYPES, PROPERTY_TYPE_LABEL } from "@/utils/format";

const num = (label: string) => z.number({ invalid_type_error: `${label} must be a number`, required_error: `${label} is required` });
const schema = z.object({
  title: z.string().trim().min(5, "At least 5 characters").max(200),
  description: z.string().trim().min(10, "At least 10 characters").max(5000),
  city: z.string().trim().min(2, "Required").max(60),
  locality: z.string().trim().min(2, "Required").max(120),
  address: z.string().max(255).optional(),
  property_type: z.enum(["apartment", "independent_house", "villa", "plot", "commercial"]),
  listing_type: z.enum(["buy", "rent"]),
  price: num("Price").positive("Must be greater than 0"),
  area_sqft: num("Area").int("Whole number").positive("Must be greater than 0"),
  bedrooms: num("Bedrooms").int().min(0).max(20),
  bathrooms: num("Bathrooms").int().min(0).max(20),
  has_parking: z.boolean(),
  furnishing: z.enum(["", "furnished", "semi_furnished", "unfurnished"]),
  status: z.enum(["active", "sold", "rented", "inactive"]),
  is_demo: z.boolean(),
  amenities: z.string(),
  imageUrls: z.string().superRefine((v, ctx) => {
    for (const line of v.split("\n").map((l) => l.trim()).filter(Boolean)) {
      try { const u = new URL(line); if (!/^https?:$/.test(u.protocol)) throw new Error(); }
      catch { ctx.addIssue({ code: "custom", message: `Not a valid http(s) URL: ${line.slice(0, 40)}` }); return; }
    }
  }),
});
type F = z.infer<typeof schema>;

const EMPTY: F = { title: "", description: "", city: "", locality: "", address: "", property_type: "apartment", listing_type: "buy", price: NaN,
  area_sqft: NaN, bedrooms: 0, bathrooms: 0, has_parking: false, furnishing: "", status: "active", is_demo: false, amenities: "", imageUrls: "" };

const fromProperty = (p: Property): F => ({ ...p, address: p.address ?? "", furnishing: p.furnishing ?? "", amenities: p.amenities.join(", "), imageUrls: p.images.map((i) => i.url).join("\n") });
const toInput = (f: F): PropertyInput => ({
  title: f.title.trim(), description: f.description.trim(), city: f.city.trim(), locality: f.locality.trim(), address: f.address?.trim() || null,
  property_type: f.property_type as PropertyType, listing_type: f.listing_type as ListingType, price: f.price, area_sqft: f.area_sqft,
  bedrooms: f.bedrooms, bathrooms: f.bathrooms, has_parking: f.has_parking, furnishing: (f.furnishing || null) as Furnishing | null,
  amenities: f.amenities.split(",").map((a) => a.trim()).filter(Boolean), status: f.status as PropertyStatus, is_demo: f.is_demo,
  images: f.imageUrls.split("\n").map((l) => l.trim()).filter(Boolean).map((url) => ({ url, alt: f.title.trim() })),
});

function PropertyForm({ existing }: { existing?: Property }) {
  const navigate = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const { register, handleSubmit, reset, setError, formState: { errors } } = useForm<F>({ resolver: zodResolver(schema), defaultValues: existing ? fromProperty(existing) : EMPTY });
  useEffect(() => { if (existing) reset(fromProperty(existing)); }, [existing, reset]);

  const save = useMutation({
    mutationFn: (f: F) => (existing ? api.admin.update(existing.id, toInput(f)) : api.admin.create(toInput(f))),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin"] }); qc.invalidateQueries({ queryKey: ["properties"] }); qc.invalidateQueries({ queryKey: ["featured"] });
      qc.invalidateQueries({ queryKey: ["property"] }); qc.invalidateQueries({ queryKey: ["facets"] });
      toast.success(existing ? "Property updated" : "Property created"); navigate("/admin"); },
    onError: (e) => setError("root", { message: e instanceof ApiError ? e.message : "Save failed" }),
  });

  const n = { valueAsNumber: true } as const;
  return (
    <div className="container-page max-w-4xl py-10">
      <PageHeader title={existing ? "Edit property" : "Add property"} subtitle="All fields are validated again by the server." actions={<Link to="/admin"><Button variant="outline">Back to admin</Button></Link>} />
      <Card className="p-6">
        <form onSubmit={handleSubmit((f) => save.mutate(f))} className="grid gap-4 sm:grid-cols-2" noValidate>
          {errors.root && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 sm:col-span-2">{errors.root.message}</p>}
          <div className="sm:col-span-2"><Field label="Title" htmlFor="t" error={errors.title?.message}><Input id="t" {...register("title")} /></Field></div>
          <div className="sm:col-span-2"><Field label="Description" htmlFor="d" error={errors.description?.message}><Textarea id="d" {...register("description")} /></Field></div>
          <Field label="City" htmlFor="city" error={errors.city?.message}><Input id="city" {...register("city")} /></Field>
          <Field label="Locality" htmlFor="loc" error={errors.locality?.message}><Input id="loc" {...register("locality")} /></Field>
          <div className="sm:col-span-2"><Field label="Address / approximate location" htmlFor="addr" error={errors.address?.message}><Input id="addr" {...register("address")} /></Field></div>
          <Field label="Property type" htmlFor="pt"><Select id="pt" {...register("property_type")}>{PROPERTY_TYPES.map((t) => <option key={t} value={t}>{PROPERTY_TYPE_LABEL[t]}</option>)}</Select></Field>
          <Field label="Listing type" htmlFor="lt"><Select id="lt" {...register("listing_type")}><option value="buy">Buy (sale)</option><option value="rent">Rent</option></Select></Field>
          <Field label="Price in INR (monthly rent if renting)" htmlFor="price" error={errors.price?.message}><Input id="price" type="number" step="any" min={0} {...register("price", n)} /></Field>
          <Field label="Area (sq ft)" htmlFor="area" error={errors.area_sqft?.message}><Input id="area" type="number" min={1} {...register("area_sqft", n)} /></Field>
          <Field label="Bedrooms" htmlFor="bed" error={errors.bedrooms?.message}><Input id="bed" type="number" min={0} {...register("bedrooms", n)} /></Field>
          <Field label="Bathrooms" htmlFor="bath" error={errors.bathrooms?.message}><Input id="bath" type="number" min={0} {...register("bathrooms", n)} /></Field>
          <Field label="Furnishing" htmlFor="fur"><Select id="fur" {...register("furnishing")}><option value="">Not specified</option>{(Object.keys(FURNISHING_LABEL) as Furnishing[]).map((f) => <option key={f} value={f}>{FURNISHING_LABEL[f]}</option>)}</Select></Field>
          <Field label="Status" htmlFor="st"><Select id="st" {...register("status")}><option value="active">Active</option><option value="inactive">Inactive (hidden)</option><option value="sold">Sold</option><option value="rented">Rented</option></Select></Field>
          <div className="sm:col-span-2"><Field label="Amenities (comma-separated)" htmlFor="am" error={errors.amenities?.message}><Input id="am" placeholder="Gym, Lift, 24x7 Security" {...register("amenities")} /></Field></div>
          <div className="sm:col-span-2"><Field label="Image URLs (one per line)" htmlFor="img" error={errors.imageUrls?.message} hint="Use images you have the right to display."><Textarea id="img" {...register("imageUrls")} /></Field></div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-gold-500" {...register("has_parking")} />Parking available</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-gold-500" {...register("is_demo")} />Mark as demonstration (fictional) listing</label>
          <div className="flex gap-3 sm:col-span-2"><Button type="submit" variant="gold" loading={save.isPending}>{existing ? "Save changes" : "Create property"}</Button><Button variant="outline" onClick={() => navigate("/admin")}>Cancel</Button></div>
        </form>
      </Card>
    </div>
  );
}

export const AddProperty = () => <PropertyForm />;

export function EditProperty() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["admin", "property", id], queryFn: () => api.admin.property(id), enabled: Number.isInteger(id) && id > 0, retry: false });
  if (q.isLoading) return <div className="container-page py-10"><Skeleton className="h-96" /></div>;
  if (q.isError || !q.data) return <div className="container-page py-10"><ErrorState message={(q.error as Error)?.message ?? "Property not found"} /></div>;
  return <PropertyForm existing={q.data} />;
}
