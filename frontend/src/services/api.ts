import type {
  AdminStats, ChatResponse, ChatSearchBody, ChatSession, ChatSessionDetail, CompareResult, Facets, Inquiry,
  InquiryInput, Page, Property, PropertyInput, PropertyStatus, TokenResponse, User, UserSummary, SearchParams,
} from "@/types";

const DEFAULT_API_URL = "http://localhost:8000";

/**
 * Turn VITE_API_URL into the final API base. Accepts "http://localhost:8000" or "http://localhost:8000/api",
 * ignores blank values (a blank `VITE_API_URL=` line must not silently send requests to the Vite dev server),
 * removes trailing slashes, and appends "/api" exactly once. "/" means "same origin" (reverse-proxy setups).
 */
export function resolveApiBase(raw?: string | null): string {
  let url = (raw ?? "").trim();
  if (!url) url = DEFAULT_API_URL;
  url = url.replace(/\/+$/, "").replace(/\/api$/i, "").replace(/\/+$/, "");
  return `${url}/api`;
}

export const API_BASE = resolveApiBase(import.meta.env.VITE_API_URL);
const BASE = API_BASE;
const TOKEN_KEY = "reg_access_token";

/*
 * Token storage: the JWT is kept in localStorage so a refresh keeps you signed in. Trade-off: any XSS bug could
 * read it. Mitigations: React escapes output, there is no dangerouslySetInnerHTML, tokens expire (60 min default)
 * and every permission is enforced again on the server. See README "Security considerations".
 */
export const tokenStore = {
  get(): string | null { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set(t: string) { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ } },
  clear() { try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ } },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

function describeError(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: { loc?: unknown[]; msg?: string }) => {
      const field = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body" && x !== "query").join(".") : "";
      return `${field ? field + ": " : ""}${(d.msg ?? "Invalid value").replace(/^Value error, /, "")}`;
    }).join("; ");
  }
  if (status === 0)
    return `Cannot reach the API at ${API_BASE}. Check that the backend is running and that this site's address is allowed by CORS_ORIGINS in backend/.env.`;
  if (body === null)
    return `Request failed (${status}). Check that VITE_API_URL points at the FastAPI backend (currently ${API_BASE}).`;
  return `Request failed (${status})`;
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>;

function buildQuery(params?: Query): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x));
    else sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function request<T>(path: string, opts: { method?: string; body?: unknown; params?: Query } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}${buildQuery(opts.params)}`, {
      method: opts.method ?? "GET", headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, describeError(null, 0));
  }
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) {
    if (res.status === 401 && token) { tokenStore.clear(); window.dispatchEvent(new Event("auth:expired")); }
    throw new ApiError(res.status, describeError(data, res.status));
  }
  return data as T;
}

export const api = {
  auth: {
    register: (b: { email: string; password: string; full_name: string; phone?: string | null }) =>
      request<TokenResponse>("/auth/register", { method: "POST", body: b }),
    login: (b: { email: string; password: string }) => request<TokenResponse>("/auth/login", { method: "POST", body: b }),
    me: () => request<User>("/auth/me"),
    logout: () => request<void>("/auth/logout", { method: "POST" }),
  },
  users: {
    updateProfile: (b: { full_name?: string; phone?: string | null }) => request<User>("/users/me", { method: "PATCH", body: b }),
    changePassword: (b: { current_password: string; new_password: string }) =>
      request<void>("/users/me/password", { method: "POST", body: b }),
    summary: () => request<UserSummary>("/users/me/summary"),
  },
  properties: {
    list: (p: SearchParams) => request<Page<Property>>("/properties", { params: p as Query }),
    get: (id: number) => request<Property>(`/properties/${id}`),
    facets: () => request<Facets>("/properties/facets"),
    compare: (ids: number[]) => request<CompareResult>("/properties/compare", { params: { ids: ids.join(",") } }),
  },
  favorites: {
    list: () => request<{ items: Property[] }>("/favorites"),
    ids: () => request<{ ids: number[] }>("/favorites/ids"),
    add: (id: number) => request<void>(`/favorites/${id}`, { method: "PUT" }),
    remove: (id: number) => request<void>(`/favorites/${id}`, { method: "DELETE" }),
  },
  inquiries: {
    create: (b: InquiryInput) => request<Inquiry>("/inquiries", { method: "POST", body: b }),
    mine: () => request<Inquiry[]>("/inquiries/mine"),
  },
  chat: {
    send: (b: ChatSearchBody) => request<ChatResponse>("/chat/message", { method: "POST", body: b }),
    sessions: () => request<ChatSession[]>("/chat/sessions"),
    session: (id: number) => request<ChatSessionDetail>(`/chat/sessions/${id}`),
    deleteSession: (id: number) => request<void>(`/chat/sessions/${id}`, { method: "DELETE" }),
  },
  admin: {
    stats: () => request<AdminStats>("/admin/stats"),
    properties: (p: SearchParams) => request<Page<Property>>("/admin/properties", { params: p as Query }),
    property: (id: number) => request<Property>(`/admin/properties/${id}`),
    create: (b: PropertyInput) => request<Property>("/admin/properties", { method: "POST", body: b }),
    update: (id: number, b: PropertyInput) => request<Property>(`/admin/properties/${id}`, { method: "PUT", body: b }),
    setStatus: (id: number, status: PropertyStatus) =>
      request<Property>(`/admin/properties/${id}/status`, { method: "PATCH", body: { status } }),
    remove: (id: number) => request<void>(`/admin/properties/${id}`, { method: "DELETE" }),
    inquiries: (status?: string) => request<Inquiry[]>("/admin/inquiries", { params: { status } }),
    setInquiryStatus: (id: number, status: Inquiry["status"]) =>
      request<Inquiry>(`/admin/inquiries/${id}`, { method: "PATCH", body: { status } }),
  },
};
