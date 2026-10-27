import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2 } from "lucide-react";
import { api, ApiError } from "@/services/api";
import { Badge, Button, Card, Field, Input, PageHeader, Textarea } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { formatDate, formatPrice } from "@/utils/format";

const schema = z.object({
  name: z.string().trim().min(2, "Enter your name").max(120),
  email: z.string().email("Enter a valid e-mail"),
  phone: z.string().refine((v) => v === "" || /^\+?[0-9][0-9 \-]{6,18}$/.test(v), "Enter a valid phone number"),
  message: z.string().trim().min(10, "Please write at least 10 characters").max(2000, "Maximum 2000 characters"),
});
type F = z.infer<typeof schema>;

export default function Contact() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [sp] = useSearchParams();
  const rawId = Number(sp.get("property"));
  const propertyId = Number.isInteger(rawId) && rawId > 0 ? rawId : undefined;
  const [sent, setSent] = useState(false);
  const prop = useQuery({ queryKey: ["property", propertyId], queryFn: () => api.properties.get(propertyId!), enabled: !!propertyId, retry: false });
  const mine = useQuery({ queryKey: ["my-inquiries", user?.id], queryFn: api.inquiries.mine, enabled: !!user });

  const { register, handleSubmit, reset, setError, formState: { errors } } = useForm<F>({
    resolver: zodResolver(schema),
    defaultValues: { name: user?.full_name ?? "", email: user?.email ?? "", phone: user?.phone ?? "", message: "" },
  });
  const submit = useMutation({
    mutationFn: (v: F) => api.inquiries.create({ property_id: propertyId ?? null, name: v.name, email: v.email, phone: v.phone || null, message: v.message }),
    onSuccess: () => { setSent(true); reset({ name: user?.full_name ?? "", email: user?.email ?? "", phone: user?.phone ?? "", message: "" });
      qc.invalidateQueries({ queryKey: ["my-inquiries"] }); qc.invalidateQueries({ queryKey: ["summary"] }); },
    onError: (e) => setError("root", { message: e instanceof ApiError ? e.message : "Could not submit your inquiry" }),
  });

  return (
    <div className="container-page max-w-3xl py-10">
      <PageHeader title={propertyId ? "Contact about this property" : "Contact us"} subtitle="Send an inquiry. It is saved in our database and visible to the site administrators." />
      {prop.data && <Card className="mb-6 flex items-center justify-between gap-3 p-4"><div><p className="font-medium">{prop.data.title}</p><p className="text-sm text-charcoal-500">{prop.data.locality}, {prop.data.city} · {formatPrice(prop.data.price, prop.data.listing_type)}</p></div><Link to={`/properties/${prop.data.id}`} className="text-sm text-gold-600 hover:underline">View</Link></Card>}
      {sent && <div role="status" className="mb-6 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" /><div><p className="font-semibold">Inquiry saved</p><p>Your message was stored successfully. Note: this demo does not send e-mail, so replies are not automatic.</p></div></div>}
      <Card className="p-6">
        <form onSubmit={handleSubmit((v) => { setSent(false); submit.mutate(v); })} className="grid gap-4 sm:grid-cols-2" noValidate>
          {errors.root && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 sm:col-span-2">{errors.root.message}</p>}
          <Field label="Name" htmlFor="c-name" error={errors.name?.message}><Input id="c-name" autoComplete="name" {...register("name")} /></Field>
          <Field label="E-mail" htmlFor="c-email" error={errors.email?.message}><Input id="c-email" type="email" autoComplete="email" {...register("email")} /></Field>
          <div className="sm:col-span-2"><Field label="Phone (optional)" htmlFor="c-phone" error={errors.phone?.message}><Input id="c-phone" type="tel" autoComplete="tel" {...register("phone")} /></Field></div>
          <div className="sm:col-span-2"><Field label="Message" htmlFor="c-msg" error={errors.message?.message}><Textarea id="c-msg" {...register("message")} /></Field></div>
          <div className="sm:col-span-2"><Button type="submit" variant="gold" loading={submit.isPending}>Submit inquiry</Button></div>
        </form>
      </Card>
      {user && mine.data && mine.data.length > 0 && (
        <section className="mt-10"><h2 className="mb-3 text-2xl font-semibold">Your inquiry history</h2>
          <ul className="space-y-3">{mine.data.map((i) => (
            <Card key={i.id} className="p-4"><div className="flex items-center justify-between gap-2"><p className="font-medium">{i.property_title ?? "General inquiry"}</p><Badge tone={i.status === "new" ? "gold" : "green"}>{i.status}</Badge></div>
              <p className="mt-1 text-sm text-charcoal-600">{i.message}</p><p className="mt-1 text-xs text-charcoal-400">{formatDate(i.created_at)}</p></Card>))}</ul></section>)}
      {!user && <p className="mt-6 text-sm text-charcoal-500"><Link to="/login" className="text-gold-600 underline">Log in</Link> to keep a history of your inquiries.</p>}
    </div>
  );
}
