import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "@/utils/cn";

type Kind = "success" | "error" | "info";
interface Toast { id: number; kind: Kind; message: string }
interface ToastApi { success: (m: string) => void; error: (m: string) => void; info: (m: string) => void }

const Ctx = createContext<ToastApi | null>(null);
let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback((kind: Kind, message: string) => {
    const id = ++counter;
    setToasts((t) => [...t.slice(-3), { id, kind, message }]);
    setTimeout(() => dismiss(id), 5000);
  }, [dismiss]);
  const api = useMemo<ToastApi>(() => ({
    success: (m) => push("success", m), error: (m) => push("error", m), info: (m) => push("info", m),
  }), [push]);

  const icon = { success: CheckCircle2, error: XCircle, info: Info };
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex flex-col items-center gap-2 px-4" role="status" aria-live="polite">
        {toasts.map((t) => {
          const Icon = icon[t.kind];
          return (
            <div key={t.id} className={cn("pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border bg-white p-3 text-sm shadow-card",
              t.kind === "success" && "border-emerald-200", t.kind === "error" && "border-red-200", t.kind === "info" && "border-charcoal-200")}>
              <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", t.kind === "success" && "text-emerald-600", t.kind === "error" && "text-red-600", t.kind === "info" && "text-gold-600")} />
              <span className="flex-1">{t.message}</span>
              <button aria-label="Dismiss notification" onClick={() => dismiss(t.id)} className="text-charcoal-400 hover:text-charcoal-900"><X className="h-4 w-4" /></button>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastApi {
  const v = useContext(Ctx);
  if (!v) throw new Error("useToast must be used inside ToastProvider");
  return v;
}
