import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Building2, LayoutDashboard, LogOut, Menu, Scale, ShieldCheck, Sparkles, User as UserIcon, X } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useCompare } from "@/hooks/useCompare";
import { useToast } from "@/hooks/useToast";
import { Button } from "@/components/ui";
import { cn } from "@/utils/cn";

const linkCls = ({ isActive }: { isActive: boolean }) =>
  cn("rounded-lg px-3 py-2 text-sm font-medium transition-colors", isActive ? "bg-white/10 text-gold-300" : "text-warm-200 hover:text-white");

export function MainLayout() {
  const { user, logout } = useAuth();
  const compare = useCompare();
  const toast = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const nav = (
    <>
      <NavLink to="/explore" className={linkCls} onClick={() => setOpen(false)}>Explore</NavLink>
      <NavLink to="/assistant" className={linkCls} onClick={() => setOpen(false)}><span className="inline-flex items-center gap-1"><Sparkles className="h-3.5 w-3.5" />AI Assistant</span></NavLink>
      <NavLink to="/compare" className={linkCls} onClick={() => setOpen(false)}>
        <span className="inline-flex items-center gap-1"><Scale className="h-3.5 w-3.5" />Compare{compare.ids.length > 0 && <span className="rounded-full bg-gold-500 px-1.5 text-xs text-charcoal-950">{compare.ids.length}</span>}</span>
      </NavLink>
      <NavLink to="/favorites" className={linkCls} onClick={() => setOpen(false)}>Favorites</NavLink>
      <NavLink to="/contact" className={linkCls} onClick={() => setOpen(false)}>Contact</NavLink>
    </>
  );

  const onLogout = async () => { await logout(); toast.success("Signed out"); navigate("/"); };

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2">Skip to content</a>
      <header className="sticky top-0 z-40 border-b border-white/10 bg-charcoal-900/95 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2 text-warm-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gold-500 text-charcoal-950"><Building2 className="h-5 w-5" /></span>
            <span className="font-serif text-xl font-semibold">Real Estate <span className="text-gold-400">GPT</span></span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{nav}</nav>
          <div className="hidden items-center gap-2 md:flex">
            {user ? (
              <>
                {user.role === "admin" && <Link to="/admin" className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-gold-300 hover:bg-white/10"><ShieldCheck className="h-4 w-4" />Admin</Link>}
                <Link to="/dashboard" className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-warm-200 hover:text-white"><LayoutDashboard className="h-4 w-4" />Dashboard</Link>
                <Link to="/profile" className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-warm-200 hover:text-white"><UserIcon className="h-4 w-4" />{user.full_name.split(" ")[0]}</Link>
                <Button variant="ghost" size="sm" onClick={onLogout} className="text-warm-200 hover:bg-white/10"><LogOut className="h-4 w-4" />Logout</Button>
              </>
            ) : (
              <>
                <Link to="/login" className="px-3 py-2 text-sm text-warm-200 hover:text-white">Log in</Link>
                <Button variant="gold" size="sm" onClick={() => navigate("/register")}>Sign up</Button>
              </>
            )}
          </div>
          <button className="rounded-lg p-2 text-warm-50 md:hidden" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        {open && (
          <div className="border-t border-white/10 px-4 pb-4 md:hidden">
            <nav className="flex flex-col py-2" aria-label="Mobile">{nav}</nav>
            <div className="flex flex-col gap-1 border-t border-white/10 pt-2 text-warm-200">
              {user ? (
                <>
                  {user.role === "admin" && <Link to="/admin" onClick={() => setOpen(false)} className="px-3 py-2">Admin dashboard</Link>}
                  <Link to="/dashboard" onClick={() => setOpen(false)} className="px-3 py-2">Dashboard</Link>
                  <Link to="/profile" onClick={() => setOpen(false)} className="px-3 py-2">Profile</Link>
                  <button className="px-3 py-2 text-left" onClick={() => { setOpen(false); void onLogout(); }}>Logout</button>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={() => setOpen(false)} className="px-3 py-2">Log in</Link>
                  <Link to="/register" onClick={() => setOpen(false)} className="px-3 py-2">Sign up</Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>
      <main id="main" className="flex-1"><Outlet /></main>
      <footer className="mt-16 bg-charcoal-950 text-charcoal-200">
        <div className="container-page grid gap-8 py-12 md:grid-cols-4">
          <div className="md:col-span-2">
            <p className="font-serif text-xl text-warm-50">Real Estate <span className="text-gold-400">GPT</span></p>
            <p className="mt-3 max-w-md text-sm text-charcoal-400">A portfolio project for AI-assisted property discovery. All listings are fictional demonstration data and the assistant uses rule-based language parsing, not a large language model.</p>
          </div>
          <div><p className="mb-3 text-sm font-semibold text-warm-50">Explore</p><ul className="space-y-2 text-sm">
            <li><Link to="/explore?listing_type=buy" className="hover:text-gold-300">Buy</Link></li>
            <li><Link to="/explore?listing_type=rent" className="hover:text-gold-300">Rent</Link></li>
            <li><Link to="/assistant" className="hover:text-gold-300">AI Assistant</Link></li></ul></div>
          <div><p className="mb-3 text-sm font-semibold text-warm-50">Account</p><ul className="space-y-2 text-sm">
            <li><Link to="/login" className="hover:text-gold-300">Log in</Link></li>
            <li><Link to="/register" className="hover:text-gold-300">Register</Link></li>
            <li><Link to="/contact" className="hover:text-gold-300">Contact</Link></li></ul></div>
        </div>
        <div className="border-t border-white/10 py-4 text-center text-xs text-charcoal-500">Demo photos via Unsplash. © {new Date().getFullYear()} Real Estate GPT (portfolio project).</div>
      </footer>
    </div>
  );
}
