import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, tokenStore } from "@/services/api";
import type { TokenResponse, User } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (data: { email: string; password: string; full_name: string; phone?: string | null }) => Promise<User>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
}
const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => tokenStore.get() !== null);
  const qc = useQueryClient();

  // Restore the session after a browser refresh (server validates the token).
  useEffect(() => {
    if (!tokenStore.get()) return;
    api.auth.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  // The API client fires this when the server answers 401 (e.g. token expired).
  useEffect(() => {
    const onExpired = () => { setUser(null); qc.clear(); };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, [qc]);

  const accept = useCallback((res: TokenResponse) => { tokenStore.set(res.access_token); setUser(res.user); return res.user; }, []);

  const value = useMemo<AuthState>(() => ({
    user, loading, setUser,
    login: async (email, password) => accept(await api.auth.login({ email, password })),
    register: async (data) => accept(await api.auth.register(data)),
    logout: async () => {
      try { await api.auth.logout(); } catch { /* token may already be invalid */ }
      tokenStore.clear(); setUser(null); qc.clear();
    },
  }), [user, loading, accept, qc]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
