import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, Info, Plus, Scale, Send, Trash2, User as UserIcon } from "lucide-react";
import { api, ApiError } from "@/services/api";
import type { ChatResponse, SearchCriteria } from "@/types";
import { Badge, Button, Card, Input, PageHeader } from "@/components/ui";
import { PropertyCard } from "@/components/PropertyCard";
import { useAuth } from "@/hooks/useAuth";
import { useCompare } from "@/hooks/useCompare";
import { useToast } from "@/hooks/useToast";
import { formatPrice } from "@/utils/format";

type Msg = { role: "user"; text: string } | { role: "assistant"; text: string; data?: ChatResponse };

const PROMPTS = [
  "Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking",
  "Show villas in Bengaluru between ₹80 lakh and ₹1.5 crore",
  "Find a rental flat in Hyderabad under ₹25,000 per month",
  "Show houses with three bedrooms and at least 1,500 square feet",
  "Compare the cheapest matching properties",
];
const INTRO: Msg = { role: "assistant", text: "Hi! Tell me what you’re looking for, e.g. city, buy or rent, budget, bedrooms. I search the demo listings in our database. I use rule-based language parsing (not a large language model), so specific requests work best." };

/** "What I understood" chips, built from the structured criteria returned by the backend parser. */
function criteriaChips(c: SearchCriteria): string[] {
  const chips: string[] = [];
  const lt = c.listing_type ?? "buy";
  if (c.listing_type) chips.push(c.listing_type === "rent" ? "Rent" : "Buy");
  c.property_types.forEach((t) => chips.push(t.replace("_", " ")));
  if (c.locality) chips.push(c.locality);
  if (c.city) chips.push(c.city);
  if (c.min_bedrooms != null || c.max_bedrooms != null)
    chips.push(c.min_bedrooms != null && c.min_bedrooms === c.max_bedrooms ? `${c.min_bedrooms} BHK` : `${c.min_bedrooms ?? 0}–${c.max_bedrooms ?? "+"} bedrooms`);
  if (c.min_bathrooms) chips.push(`${c.min_bathrooms}+ baths`);
  if (c.min_price != null) chips.push(`≥ ${formatPrice(c.min_price, lt)}`);
  if (c.max_price != null) chips.push(`≤ ${formatPrice(c.max_price, lt)}`);
  if (c.min_area) chips.push(`≥ ${c.min_area} sq ft`);
  if (c.max_area) chips.push(`≤ ${c.max_area} sq ft`);
  if (c.has_parking) chips.push("Parking");
  if (c.furnishing) chips.push(c.furnishing.replace("_", " "));
  c.amenities.forEach((a) => chips.push(a));
  return chips;
}

export default function Assistant() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const compare = useCompare();
  const toast = useToast();
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const [messages, setMessages] = useState<Msg[]>([INTRO]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [context, setContext] = useState<SearchCriteria | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const autoSent = useRef(false);

  const sessions = useQuery({ queryKey: ["chat-sessions", user?.id], queryFn: api.chat.sessions, enabled: !!user });

  const send = useMutation({
    mutationFn: (v: { message: string; override?: SearchCriteria }) =>
      api.chat.send({ message: v.message, session_id: sessionId, context_criteria: context, criteria_override: v.override ?? null }),
    onSuccess: (res) => {
      setMessages((m) => [...m, { role: "assistant", text: res.reply, data: res }]);
      if (res.session_id) { setSessionId(res.session_id); qc.invalidateQueries({ queryKey: ["chat-sessions"] }); qc.invalidateQueries({ queryKey: ["summary"] }); }
      if (res.intent === "search" || res.intent === "compare") setContext(res.criteria);
    },
    onError: (e) => {
      const msg = e instanceof ApiError ? e.message : "Something went wrong";
      setMessages((m) => [...m, { role: "assistant", text: `Sorry, I couldn’t complete that: ${msg}` }]);
    },
  });

  const submit = (message: string, override?: SearchCriteria) => {
    const text = message.trim();
    if (!text || send.isPending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    send.mutate({ message: text, override });
  };

  // Support deep links such as /assistant?q=... (sent once)
  useEffect(() => {
    const q = sp.get("q");
    if (q && !autoSent.current) { autoSent.current = true; setSp({}, { replace: true }); submit(q); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView?.({ behavior: "smooth" }); }, [messages, send.isPending]);

  const newChat = () => { setMessages([INTRO]); setSessionId(null); setContext(null); };
  const openSession = async (id: number) => {
    try {
      const s = await api.chat.session(id);
      setMessages([INTRO, ...s.messages.map((m): Msg => ({ role: m.role, text: m.content }))]);
      setSessionId(id); setContext(null);
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "Could not open chat"); }
  };
  const removeSession = async (id: number) => {
    try { await api.chat.deleteSession(id); if (id === sessionId) newChat(); qc.invalidateQueries({ queryKey: ["chat-sessions"] }); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "Could not delete chat"); }
  };
  const openCompare = (ids: number[]) => { compare.set(ids); navigate(`/compare?ids=${ids.join(",")}`); };

  return (
    <div className="container-page py-10">
      <PageHeader title="Real Estate GPT assistant" subtitle="Describe your ideal property in plain English. Results come straight from the database." />
      <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
        <aside className="space-y-4">
          <Card className="p-4">
            <p className="mb-3 text-sm font-semibold">Try asking</p>
            <ul className="space-y-2">{PROMPTS.map((p) => <li key={p}><button onClick={() => submit(p)} className="w-full rounded-lg border border-charcoal-100 p-2.5 text-left text-xs text-charcoal-700 transition hover:border-gold-500 hover:bg-warm-200/60">{p}</button></li>)}</ul>
          </Card>
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between"><p className="text-sm font-semibold">Chat history</p><Button size="sm" variant="outline" onClick={newChat}><Plus className="h-3.5 w-3.5" />New</Button></div>
            {!user ? <p className="text-xs text-charcoal-500"><Link to="/login" className="text-gold-600 underline">Sign in</Link> to save your chats. Anonymous chats aren’t stored.</p> :
              sessions.data?.length ? <ul className="space-y-1">{sessions.data.map((s) => (
                <li key={s.id} className="flex items-center gap-1"><button onClick={() => openSession(s.id)} className={`flex-1 truncate rounded-lg px-2 py-1.5 text-left text-xs hover:bg-warm-200 ${s.id === sessionId ? "bg-warm-200 font-medium" : ""}`}>{s.title}</button>
                  <button aria-label={`Delete chat ${s.title}`} onClick={() => removeSession(s.id)} className="p-1 text-charcoal-400 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button></li>))}</ul> :
                <p className="text-xs text-charcoal-500">No saved chats yet.</p>}
          </Card>
        </aside>

        <section className="flex min-h-[32rem] flex-col rounded-2xl border border-charcoal-100 bg-white shadow-card" aria-label="Conversation">
          <div className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex gap-3"}>
                {m.role === "assistant" && <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-charcoal-900 text-gold-400"><Bot className="h-4 w-4" /></span>}
                <div className={m.role === "user" ? "max-w-[85%] rounded-2xl rounded-tr-sm bg-charcoal-900 px-4 py-2.5 text-sm text-warm-50" : "min-w-0 flex-1 space-y-3"}>
                  {m.role === "user" && <span className="sr-only"><UserIcon /> You: </span>}
                  <p className={m.role === "assistant" ? "whitespace-pre-line rounded-2xl rounded-tl-sm bg-warm-200/70 px-4 py-2.5 text-sm" : ""}>{m.text}</p>
                  {m.role === "assistant" && m.data && <AssistantExtras data={m.data} onSuggest={(label, c) => submit(label, c)} onCompare={openCompare} />}
                </div>
              </div>
            ))}
            {send.isPending && <p className="text-sm text-charcoal-500" role="status">Searching the database…</p>}
            <div ref={endRef} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); submit(input); }} className="flex gap-2 border-t border-charcoal-100 p-3" aria-label="Send a message">
            <Input aria-label="Your message" maxLength={1000} placeholder="e.g. 2BHK apartment in Pune under 70 lakh with parking" value={input} onChange={(e) => setInput(e.target.value)} />
            <Button type="submit" variant="gold" loading={send.isPending} aria-label="Send"><Send className="h-4 w-4" /></Button>
          </form>
        </section>
      </div>
    </div>
  );
}

function AssistantExtras({ data, onSuggest, onCompare }: { data: ChatResponse; onSuggest: (label: string, c: SearchCriteria) => void; onCompare: (ids: number[]) => void }) {
  const chips = criteriaChips(data.criteria);
  return (
    <div className="space-y-3">
      {chips.length > 0 && <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-charcoal-500">What I understood</p><div className="flex flex-wrap gap-1.5">{chips.map((c) => <Badge key={c} tone="gold">{c}</Badge>)}</div></div>}
      {data.warnings.filter((w) => !w.includes("buy or rent")).map((w) => <p key={w} className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-800"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{w}</p>)}
      {data.assumptions.map((a) => <p key={a} className="flex items-start gap-2 text-xs text-charcoal-500"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />{a}</p>)}
      {data.compare_ids.length >= 2 && <Button variant="gold" size="sm" onClick={() => onCompare(data.compare_ids)}><Scale className="h-4 w-4" />Open comparison table ({data.compare_ids.length})</Button>}
      {data.matches.length > 0 && <div className="grid gap-4 sm:grid-cols-2">{data.matches.map((m) => <PropertyCard key={m.property.id} property={m.property} reasons={m.reasons} />)}</div>}
      {data.suggestions.length > 0 && <div className="space-y-2"><p className="text-xs font-semibold uppercase tracking-wide text-charcoal-500">Suggested adjustments</p>
        <div className="flex flex-wrap gap-2">{data.suggestions.map((s) => <Button key={s.label} variant="outline" size="sm" onClick={() => onSuggest(s.label, s.criteria)}>{s.label} ({s.match_count} match{s.match_count > 1 ? "es" : ""})</Button>)}</div></div>}
      {data.total_matches > data.matches.length && data.intent === "search" && <Link to="/explore" className="text-xs text-gold-600 underline">Showing {data.matches.length} of {data.total_matches}. Refine your request or use Explore filters.</Link>}
    </div>
  );
}
