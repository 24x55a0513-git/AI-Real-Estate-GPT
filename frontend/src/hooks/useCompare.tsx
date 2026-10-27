import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useToast } from "@/hooks/useToast";

export const MAX_COMPARE = 4;
const KEY = "reg_compare_ids";

interface CompareState {
  ids: number[]; has: (id: number) => boolean; toggle: (id: number) => void; remove: (id: number) => void;
  set: (ids: number[]) => void; clear: () => void;
}
const Ctx = createContext<CompareState | null>(null);

function load(): number[] {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((n) => Number.isInteger(n)).slice(0, MAX_COMPARE) : [];
  } catch { return []; }
}

/** Comparison list lives in the browser (no account needed) and is validated by the server when compared. */
export function CompareProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<number[]>(load);
  const toast = useToast();
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(ids)); } catch { /* ignore */ } }, [ids]);

  const toggle = useCallback((id: number) => {
    setIds((cur) => {
      if (cur.includes(id)) return cur.filter((x) => x !== id);
      if (cur.length >= MAX_COMPARE) { toast.info(`You can compare up to ${MAX_COMPARE} properties.`); return cur; }
      return [...cur, id];
    });
  }, [toast]);

  const value = useMemo<CompareState>(() => ({
    ids, has: (id) => ids.includes(id), toggle,
    remove: (id) => setIds((c) => c.filter((x) => x !== id)),
    set: (n) => setIds([...new Set(n)].slice(0, MAX_COMPARE)), clear: () => setIds([]),
  }), [ids, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCompare(): CompareState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCompare must be used inside CompareProvider");
  return v;
}
