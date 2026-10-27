import { useState } from "react";
import { cn } from "@/utils/cn";

const FALLBACK = "data:image/svg+xml;utf8," + encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'><rect width='400' height='300' fill='#e6e7e9'/>` +
  `<path d='M120 170 200 105l80 65v60h-50v-40h-60v40h-50z' fill='#b8913f' opacity='.55'/>` +
  `<text x='200' y='262' font-family='sans-serif' font-size='14' fill='#5b5f68' text-anchor='middle'>Image unavailable</text></svg>`);

/** <img> with lazy loading and a local SVG fallback if the remote photo fails to load. */
export function PropertyImage({ src, alt, className }: { src?: string; alt: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <img src={failed || !src ? FALLBACK : src} alt={alt} loading="lazy" onError={() => setFailed(true)}
      className={cn("h-full w-full object-cover", className)} />
  );
}
