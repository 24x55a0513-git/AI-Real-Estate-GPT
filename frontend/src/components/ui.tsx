import { forwardRef, useEffect, useRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode,
  type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";

/* shadcn/ui-style primitives (hand-written, same design conventions) */

type Variant = "primary" | "gold" | "outline" | "ghost" | "danger";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-charcoal-900 text-warm-50 hover:bg-charcoal-700",
  gold: "bg-gold-500 text-charcoal-950 hover:bg-gold-400",
  outline: "border border-charcoal-200 bg-white text-charcoal-900 hover:bg-warm-200",
  ghost: "text-charcoal-700 hover:bg-charcoal-100",
  danger: "bg-red-600 text-white hover:bg-red-700",
};
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean;
}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, type = "button", ...rest }, ref) {
  return (
    <button ref={ref} type={type} disabled={disabled || loading}
      className={cn("inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" && "h-9 px-3 text-sm", size === "md" && "h-11 px-5 text-sm", size === "lg" && "h-12 px-7 text-base",
        VARIANTS[variant], className)} {...rest}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

const FIELD = "w-full rounded-xl border border-charcoal-200 bg-white px-3.5 text-sm text-charcoal-900 placeholder:text-charcoal-400 focus:border-gold-500";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...p }, ref) {
  return <input ref={ref} className={cn(FIELD, "h-11", className)} {...p} />;
});
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, ...p }, ref) {
  return <select ref={ref} className={cn(FIELD, "h-11 pr-8", className)} {...p} />;
});
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...p }, ref) {
  return <textarea ref={ref} className={cn(FIELD, "min-h-[110px] py-2.5", className)} {...p} />;
});

export function Field({ label, error, hint, htmlFor, children }: { label: string; error?: string; hint?: string; htmlFor: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-charcoal-800">{label}</label>
      {children}
      {hint && !error && <p className="text-xs text-charcoal-500">{hint}</p>}
      {error && <p role="alert" className="text-xs font-medium text-red-600">{error}</p>}
    </div>
  );
}

export function Badge({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "gold" | "dark" | "green" | "red"; className?: string }) {
  const tones = { neutral: "bg-charcoal-100 text-charcoal-700", gold: "bg-gold-300/40 text-gold-700", dark: "bg-charcoal-900 text-warm-50",
    green: "bg-emerald-100 text-emerald-800", red: "bg-red-100 text-red-800" };
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)}>{children}</span>;
}

export const Card = ({ className, children }: { className?: string; children: ReactNode }) =>
  <div className={cn("rounded-2xl border border-charcoal-100 bg-white shadow-card", className)}>{children}</div>;

export const Skeleton = ({ className }: { className?: string }) =>
  <div aria-hidden className={cn("animate-pulse rounded-xl bg-charcoal-100", className)} />;

export const Spinner = ({ label = "Loading" }: { label?: string }) =>
  <div role="status" className="flex items-center justify-center gap-2 py-10 text-charcoal-500"><Loader2 className="h-5 w-5 animate-spin" /> {label}…</div>;

export function EmptyState({ title, message, action }: { title: string; message?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-charcoal-200 bg-white/60 px-6 py-14 text-center">
      <Inbox className="mb-3 h-9 w-9 text-charcoal-400" aria-hidden />
      <h3 className="text-lg font-semibold">{title}</h3>
      {message && <p className="mt-1 max-w-md text-sm text-charcoal-500">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center rounded-2xl border border-red-200 bg-red-50 px-6 py-12 text-center">
      <AlertTriangle className="mb-3 h-8 w-8 text-red-500" aria-hidden />
      <p className="font-medium text-red-800">Something went wrong</p>
      <p className="mt-1 max-w-md text-sm text-red-700">{message}</p>
      {onRetry && <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

/** Accessible modal dialog built on the native <dialog> element (focus trap + Escape handled by the browser). */
export function Dialog({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      if (typeof d.showModal === "function") d.showModal();
      else d.setAttribute("open", "");
    }
    if (!open && d.open) {
      if (typeof d.close === "function") d.close();
      else d.removeAttribute("open");
    }
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} aria-labelledby="dialog-title"
      className="w-[min(92vw,28rem)] rounded-2xl p-0 shadow-2xl backdrop:bg-charcoal-950/50">
      <div className="p-6">
        <h2 id="dialog-title" className="text-xl font-semibold">{title}</h2>
        <div className="mt-3">{children}</div>
      </div>
    </dialog>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", danger, loading, onConfirm, onCancel }:
  { open: boolean; title: string; message: string; confirmLabel?: string; danger?: boolean; loading?: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <Dialog open={open} onClose={onCancel} title={title}>
      <p className="text-sm text-charcoal-600">{message}</p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button variant={danger ? "danger" : "primary"} loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Dialog>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-charcoal-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export const DemoNotice = () => (
  <p className="rounded-lg bg-gold-300/30 px-3 py-2 text-xs text-gold-700">
    All listings are <strong>fictional demonstration data</strong>, not verified real-world properties.
  </p>
);
