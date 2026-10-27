import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Heart, MessageSquare, Sparkles } from "lucide-react";
import { api } from "@/services/api";
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { formatDate } from "@/utils/format";

export default function Dashboard() {
  const { user } = useAuth();
  const summary = useQuery({ queryKey: ["summary", user?.id], queryFn: api.users.summary });
  const inquiries = useQuery({ queryKey: ["my-inquiries", user?.id], queryFn: api.inquiries.mine });
  const sessions = useQuery({ queryKey: ["chat-sessions", user?.id], queryFn: api.chat.sessions });
  const stats = [
    { label: "Saved properties", value: summary.data?.favorites, icon: Heart, to: "/favorites" },
    { label: "Inquiries sent", value: summary.data?.inquiries, icon: MessageSquare, to: "/contact" },
    { label: "Assistant chats", value: summary.data?.chat_sessions, icon: Sparkles, to: "/assistant" },
  ];
  return (
    <div className="container-page py-10">
      <PageHeader title={`Welcome, ${user?.full_name.split(" ")[0]}`} subtitle="Your activity at a glance."
        actions={user?.role === "admin" ? <Link to="/admin"><Button variant="gold">Admin dashboard</Button></Link> : undefined} />
      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} to={s.to}><Card className="p-5 transition hover:-translate-y-0.5">
            <s.icon className="h-5 w-5 text-gold-600" />
            {summary.isLoading ? <Skeleton className="mt-3 h-9 w-16" /> : <p className="mt-2 font-serif text-4xl font-semibold">{s.value ?? "–"}</p>}
            <p className="text-sm text-charcoal-500">{s.label}</p></Card></Link>))}
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card className="p-5"><h2 className="mb-4 text-xl font-semibold">My inquiries</h2>
          {inquiries.data?.length ? <ul className="divide-y divide-charcoal-100">{inquiries.data.slice(0, 5).map((i) => (
            <li key={i.id} className="py-3 text-sm"><div className="flex items-center justify-between gap-2"><span className="font-medium">{i.property_title ?? "General inquiry"}</span><Badge tone={i.status === "new" ? "gold" : "green"}>{i.status}</Badge></div>
              <p className="mt-1 line-clamp-2 text-charcoal-500">{i.message}</p><p className="mt-1 text-xs text-charcoal-400">{formatDate(i.created_at)}</p></li>))}</ul> :
            <EmptyState title="No inquiries yet" message="Open a property and choose “Contact About This Property”." />}
        </Card>
        <Card className="p-5"><h2 className="mb-4 text-xl font-semibold">Recent assistant chats</h2>
          {sessions.data?.length ? <ul className="divide-y divide-charcoal-100">{sessions.data.slice(0, 5).map((s) => (
            <li key={s.id} className="py-3 text-sm"><Link to="/assistant" className="font-medium hover:text-gold-600">{s.title}</Link><p className="text-xs text-charcoal-400">{formatDate(s.updated_at)}</p></li>))}</ul> :
            <EmptyState title="No chats yet" message="Ask the assistant to find a property." action={<Link to="/assistant"><Button variant="gold" size="sm">Open assistant</Button></Link>} />}
        </Card>
      </div>
    </div>
  );
}
