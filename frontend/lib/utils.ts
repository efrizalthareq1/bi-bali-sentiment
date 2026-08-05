import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPct(n: number) {
  return `${n.toFixed(1)}%`;
}

export function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export const SOURCE_LABELS: Record<string, string> = {
  x: "X (Twitter)",
  instagram: "Instagram",
  instagram_comment: "Komentar IG",
  tiktok: "TikTok",
  news: "Berita",
  manual: "Manual",
  threads: "Threads",
  youtube: "YouTube",
};

export const SENTIMENT_LABELS: Record<string, string> = {
  positif: "Positif",
  negatif: "Negatif",
  netral: "Netral",
};
