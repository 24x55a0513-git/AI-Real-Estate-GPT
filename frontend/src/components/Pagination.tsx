import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui";

export function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-center gap-3">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft className="h-4 w-4" />Previous</Button>
      <span className="text-sm text-charcoal-600">Page {page} of {totalPages}</span>
      <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Next<ChevronRight className="h-4 w-4" /></Button>
    </nav>
  );
}
