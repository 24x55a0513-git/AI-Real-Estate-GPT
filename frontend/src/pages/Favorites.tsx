import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Button, EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { PropertyCard, PropertyCardSkeleton } from "@/components/PropertyCard";
import { useAuth } from "@/hooks/useAuth";

export default function Favorites() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["favorites", user?.id], queryFn: api.favorites.list });
  return (
    <div className="container-page py-10">
      <PageHeader title="Saved properties" subtitle="Your favorites are stored in your account and available on any device." />
      {q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> :
        q.isLoading ? <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 3 }, (_, i) => <PropertyCardSkeleton key={i} />)}</div> :
        q.data && q.data.items.length === 0 ? <EmptyState title="No saved properties yet" message="Tap the heart on any listing to save it here." action={<Link to="/explore"><Button variant="gold">Explore properties</Button></Link>} /> :
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{q.data?.items.map((p) => <PropertyCard key={p.id} property={p} />)}</div>}
    </div>
  );
}
