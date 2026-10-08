"use client";

import { Filters } from "@/lib/api";

type Props = {
  value: Filters;
  onChange: (next: Filters) => void;
  keywords?: string[];
};

export function GlobalFilters({ value, onChange, keywords = [] }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...value, ...patch });
  const textKeywords = keywords.filter((k) => !k.startsWith("#"));
  const hashtagKeywords = keywords.filter((k) => k.startsWith("#"));

  return (
    <div className="rounded-xl border border-border bg-card/80 p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Filter Global</h2>
        <button
          type="button"
          className="text-xs text-primary hover:underline"
          onClick={() =>
            onChange({
              source: "",
              sentiment: "",
              keyword: "",
              date_from: "",
              date_to: "",
              q: "",
            })
          }
        >
          Reset
        </button>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Platform
          <select
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.source || ""}
            onChange={(e) => set({ source: e.target.value })}
          >
            <option value="">Semua</option>
            <option value="x">X (Twitter)</option>
            <option value="instagram">Instagram</option>
            <option value="instagram_comment">Komentar IG</option>
            <option value="tiktok">TikTok</option>
            <option value="news">Berita</option>
            <option value="manual">Manual</option>
            <option value="threads">Threads</option>
            <option value="youtube">YouTube</option>
            <option value="outlook">Outlook</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Sentimen
          <select
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.sentiment || ""}
            onChange={(e) => set({ sentiment: e.target.value })}
          >
            <option value="">Semua</option>
            <option value="positif">Positif</option>
            <option value="negatif">Negatif</option>
            <option value="netral">Netral</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground sm:col-span-2">
          Cari keyword
          <input
            list="keyword-suggestions"
            type="search"
            placeholder="Ketik keyword… mis. BI Aceh, QRIS Aceh, inflasi Aceh"
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.keyword || ""}
            onChange={(e) => set({ keyword: e.target.value })}
          />
          <datalist id="keyword-suggestions">
            {textKeywords.map((k) => (
              <option key={k} value={k} />
            ))}
            {hashtagKeywords.map((k) => (
              <option key={k} value={k} />
            ))}
          </datalist>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Dari tanggal
          <input
            type="date"
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.date_from?.slice(0, 10) || ""}
            onChange={(e) =>
              set({ date_from: e.target.value ? `${e.target.value}T00:00:00` : "" })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Sampai tanggal
          <input
            type="date"
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.date_to?.slice(0, 10) || ""}
            onChange={(e) =>
              set({ date_to: e.target.value ? `${e.target.value}T23:59:59` : "" })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground sm:col-span-2">
          Cari teks postingan
          <input
            type="search"
            placeholder="Cari kata dalam isi post / berita..."
            className="h-10 rounded-lg border border-border bg-input px-3 text-sm text-foreground"
            value={value.q || ""}
            onChange={(e) => set({ q: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}
