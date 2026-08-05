import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        className
      )}
      {...props}
    />
  );
}

export function SentimentBadge({ sentiment }: { sentiment?: string }) {
  if (!sentiment) {
    return <Badge className="bg-muted text-muted-foreground">Belum dianalisis</Badge>;
  }
  const styles: Record<string, string> = {
    positif: "bg-teal-100 text-teal-800 ring-1 ring-teal-200",
    negatif: "bg-red-100 text-red-800 ring-1 ring-red-200",
    netral: "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
  };
  const labels: Record<string, string> = {
    positif: "Positif",
    negatif: "Negatif",
    netral: "Netral",
  };
  return (
    <Badge className={styles[sentiment] || "bg-muted"}>
      {labels[sentiment] || sentiment}
    </Badge>
  );
}
