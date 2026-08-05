"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SNAForceCanvas } from "@/components/sna-force-canvas";
import type { SNAGraph, SNANode } from "@/lib/api";

type Props = {
  data: SNAGraph | null;
  loading?: boolean;
};

export function SNAGraphPanel({ data, loading }: Props) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<SNANode | null>(null);

  const filteredTop = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    if (!q) return data.top_nodes;
    return data.top_nodes.filter((n) => n.label.toLowerCase().includes(q));
  }, [data, query]);

  if (loading && !data) {
    return (
      <Card>
        <CardContent className="p-10 text-center text-muted-foreground">
          Memuat Sentiment Network Analysis...
        </CardContent>
      </Card>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>SNA by Sentiment</CardTitle>
          <CardDescription>Belum ada data cukup untuk membangun jaringan.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { stats, sentiments } = data;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border pb-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary">
              SNA Graph
            </p>
            <CardTitle className="mt-1">SNA by Sentiment</CardTitle>
            <CardDescription>
              Jaringan keyword, akun/outlet, dan topik — diwarnai menurut klaster sentimen.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[1fr_300px]">
        <div className="relative min-h-[420px]">
          <SNAForceCanvas
            data={data}
            highlightId={selected?.id}
            onSelectNode={setSelected}
          />
          <div className="pointer-events-none absolute inset-0 hidden md:block">
            {data.clusters.map((c, idx) => {
              const positions = [
                "left-3 top-3",
                "left-3 bottom-3",
                "right-[320px] top-3",
                "right-[320px] bottom-16",
              ];
              return (
                <div
                  key={c.id}
                  className={`absolute max-w-[220px] rounded-lg border border-border/80 bg-white/90 p-3 shadow-sm backdrop-blur ${positions[idx % positions.length]}`}
                >
                  <p className="text-[11px] font-semibold" style={{ color: c.color }}>
                    {c.label}
                  </p>
                  <ul className="mt-2 space-y-1 text-[11px] leading-snug text-slate-600">
                    {c.points.slice(0, 3).map((p) => (
                      <li key={p}>• {p}</li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>

        <aside className="flex flex-col gap-4 rounded-xl border border-border bg-card/60 p-4">
          <div>
            <h3 className="text-sm font-semibold">Node Insight</h3>
            <p className="text-xs text-muted-foreground">Profil graf & ranking node</p>
          </div>

          <div>
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Graph Profiles
            </p>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">All Mentions</dt>
              <dd className="text-right font-medium">{stats.all_mentions.toLocaleString("id-ID")}</dd>
              <dt className="text-muted-foreground">All Sources</dt>
              <dd className="text-right font-medium">{stats.all_sources.toLocaleString("id-ID")}</dd>
              <dt className="text-muted-foreground">Nodes</dt>
              <dd className="text-right font-medium">{stats.nodes.toLocaleString("id-ID")}</dd>
              <dt className="text-muted-foreground">Edges</dt>
              <dd className="text-right font-medium">{stats.edges.toLocaleString("id-ID")}</dd>
              <dt className="text-muted-foreground">Density</dt>
              <dd className="text-right font-medium">{stats.density_pct}%</dd>
              <dt className="text-muted-foreground">Avg Degree</dt>
              <dd className="text-right font-medium">{stats.avg_degree}</dd>
            </dl>
          </div>

          <div>
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Sentiments
            </p>
            <div className="space-y-2">
              {[
                { key: "positif", label: "Positive", pct: sentiments.positif_pct, color: "bg-emerald-500" },
                { key: "netral", label: "Neutral", pct: sentiments.netral_pct, color: "bg-zinc-400" },
                { key: "negatif", label: "Negative", pct: sentiments.negatif_pct, color: "bg-red-500" },
              ].map((s) => (
                <div key={s.key}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span>{s.label}</span>
                    <span className="text-muted-foreground">{s.pct}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div className={`h-full ${s.color}`} style={{ width: `${s.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Top Nodes ({filteredTop.length})
            </p>
            <div className="relative mb-2">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cari keyword / akun..."
                className="h-9 w-full rounded-lg border border-border bg-input pl-8 pr-3 text-xs text-foreground"
              />
            </div>
            <ul className="max-h-56 space-y-1 overflow-y-auto text-xs">
              {filteredTop.map((n, i) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() =>
                      setSelected({
                        id: n.id,
                        label: n.label,
                        type: n.type,
                        sentiment: n.sentiment,
                        cluster: n.cluster,
                        size: n.count,
                        color:
                          n.cluster === "positif"
                            ? "#22c55e"
                            : n.cluster === "negatif"
                              ? "#ef4444"
                              : n.cluster === "media"
                                ? "#60a5fa"
                                : "#a1a1aa",
                      })
                    }
                    className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left hover:bg-muted ${
                      selected?.id === n.id ? "bg-muted" : ""
                    }`}
                  >
                    <span className="truncate">
                      <span className="mr-2 text-muted-foreground">{i + 1}.</span>
                      {n.label}
                    </span>
                    <span className="ml-2 shrink-0 text-muted-foreground">{n.count}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {selected && (
            <div className="rounded-lg border border-border bg-slate-50 p-3 text-xs">
              <p className="font-medium">{selected.label}</p>
              <p className="mt-1 text-muted-foreground">
                {selected.type} · {selected.sentiment} · size {selected.size}
              </p>
            </div>
          )}
        </aside>
      </CardContent>
    </Card>
  );
}
