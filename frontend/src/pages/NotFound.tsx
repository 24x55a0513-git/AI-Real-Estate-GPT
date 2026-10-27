import { Link } from "react-router-dom";
import { Button } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="container-page flex flex-col items-center py-24 text-center">
      <p className="font-serif text-8xl font-semibold text-gold-500">404</p>
      <h1 className="mt-4 text-3xl font-semibold">This page could not be found</h1>
      <p className="mt-2 max-w-md text-charcoal-500">The link may be broken or the page may have moved.</p>
      <div className="mt-6 flex gap-3"><Link to="/"><Button variant="gold">Go home</Button></Link><Link to="/explore"><Button variant="outline">Explore properties</Button></Link></div>
    </div>
  );
}
