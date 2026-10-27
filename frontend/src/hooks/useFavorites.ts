import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import { api, ApiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";

/** Favorites are stored in MySQL; this hook keeps the UI in sync via the TanStack Query cache. */
export function useFavorites() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const idsQuery = useQuery({ queryKey: ["favorite-ids", user?.id], queryFn: api.favorites.ids, enabled: !!user });
  const ids = idsQuery.data?.ids ?? [];

  const mutation = useMutation({
    mutationFn: ({ id, add }: { id: number; add: boolean }) => (add ? api.favorites.add(id) : api.favorites.remove(id)),
    onSuccess: (_d, v) => {
      qc.invalidateQueries({ queryKey: ["favorite-ids"] });
      qc.invalidateQueries({ queryKey: ["favorites"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      toast.success(v.add ? "Saved to favorites" : "Removed from favorites");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not update favorites"),
  });

  const toggle = (id: number) => {
    if (!user) {
      toast.info("Please sign in to save properties.");
      navigate("/login", { state: { from: location.pathname + location.search } });
      return;
    }
    mutation.mutate({ id, add: !ids.includes(id) });
  };
  return { ids, isFavorite: (id: number) => ids.includes(id), toggle, pending: mutation.isPending };
}
