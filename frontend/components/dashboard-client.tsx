"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  PlatformChart,
  SummaryCards,
  TopicRanking,
  TrendChart,
  WordCloud,
} from "@/components/dashboard-charts";
import { GlobalFilters } from "@/components/global-filters";
import { PostsTable } from "@/components/posts-table";
import { SNAGraphPanel } from "@/components/sna-graph-panel";
import { TopicFocusBar } from "@/components/topic-focus-bar";
import { Button } from "@/components/ui/button";
import {
  api,
  getApiBaseUrl,
  type DashboardOverview,
  type Filters,
  type PostListResponse,
  type SNAGraph,
} from "@/lib/api";
import { buildSnaFromPosts } from "@/lib/sna";

const ACEH_DEFAULT_Q =
  "Bank Indonesia Aceh OR BI Aceh OR KPwBI Aceh OR QRIS Aceh OR #BIAceh OR #BankIndonesiaAceh";

export function DashboardClient() {
  const [filters, setFilters] = useState<Filters>({
    q: ACEH_DEFAULT_Q,
  });
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [sna, setSna] = useState<SNAGraph | null>(null);
  const [posts, setPosts] = useState<PostListResponse | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncNote, setSyncNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        source: filters.source || "",
        sentiment: filters.sentiment || "",
        keyword: filters.keyword || "",
        date_from: filters.date_from || "",
        date_to: filters.date_to || "",
        q: filters.q || "",
      }),
    [filters]
  );

  const cleanFilters = useMemo(() => {
    const parsed = JSON.parse(filterKey) as Filters;
    const next: Filters = {};
    Object.entries(parsed).forEach(([k, v]) => {
      if (v) next[k as keyof Filters] = v;
    });
    return next;
  }, [filterKey]);

  const isAcehFocus = useMemo(() => {
    const blob = `${filters.keyword || ""} ${filters.q || ""}`.toLowerCase();
    return /bank indonesia aceh|bi aceh|kpwbi|qris aceh|#biaceh/.test(blob);
  }, [filters.keyword, filters.q]);

  const load = useCallback(
    async (pageNum: number) => {
      setLoading(true);
      setError(null);
      try {
        const [ov, pl, kw] = await Promise.all([
          api.overview(cleanFilters),
          api.posts({ ...cleanFilters, page: pageNum, page_size: 15 }),
          api.keywords(),
        ]);
        setOverview(ov);
        setPosts(pl);
        setKeywords(kw.map((k) => k.keyword));

        try {
          const [snaPage1, snaPage2] = await Promise.all([
            api.posts({ ...cleanFilters, page: 1, page_size: 100 }),
            api.posts({ ...cleanFilters, page: 2, page_size: 100 }),
          ]);
          const snaItems = [...(snaPage1.items || []), ...(snaPage2.items || [])];
          setSna(buildSnaFromPosts(snaItems, 120));
        } catch {
          setSna(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Gagal memuat dashboard");
      } finally {
        setLoading(false);
      }
    },
    [cleanFilters]
  );

  useEffect(() => {
    setPage(1);
  }, [filterKey]);

  useEffect(() => {
    void load(page);
  }, [load, page]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncNote(null);
    setError(null);
    const notes: string[] = [];
    try {
      try {
        await api.seedHashtags();
      } catch {
        /* keywords seed optional */
      }
      try {
        const news = await api.syncNews();
        notes.push(`Berita +${news.inserted}`);
      } catch (err) {
        notes.push(`Berita gagal: ${err instanceof Error ? err.message : "error"}`);
      }

      for (const id of ["x", "instagram", "youtube", "threads"] as const) {
        try {
          const res = await api.syncSource(id);
          notes.push(`${id} +${res.inserted}`);
        } catch {
          notes.push(`${id} dilewati`);
        }
      }

      try {
        const analyzed = await api.analyzePending();
        notes.push(`analisis ${analyzed.inserted || 0}`);
      } catch {
        /* optional */
      }

      setSyncNote(notes.join(" · "));
      await load(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal sinkronisasi");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">
            KPwBI Aceh
          </p>
          <h1 className="font-display mt-1 text-3xl font-semibold tracking-tight text-foreground">
            Dashboard Sentimen
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Monitoring percakapan publik terkait{" "}
            <span className="font-medium text-foreground">Bank Indonesia Aceh</span>.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void load(page)} disabled={loading || syncing}>
            {loading ? "Memuat..." : "Muat ulang"}
          </Button>
          <Button onClick={() => void handleSync()} disabled={syncing || loading}>
            {syncing ? "Menyinkronkan..." : "Sinkronkan berita & sosmed"}
          </Button>
        </div>
      </div>

      {syncNote && (
        <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground">
          Sinkronisasi selesai: {syncNote}
        </div>
      )}

      <TopicFocusBar
        activeKeyword={filters.keyword}
        onSelect={(topic) => {
          if (!topic) {
            // "Semua": hapus fokus topik; tetap pakai query Aceh yang luas
            setFilters({
              source: filters.source,
              sentiment: filters.sentiment,
              date_from: filters.date_from,
              date_to: filters.date_to,
              q: ACEH_DEFAULT_Q,
            });
            return;
          }
          setFilters({
            ...filters,
            keyword: topic.keyword,
            q: topic.q || topic.keyword,
          });
        }}
      />

      <GlobalFilters value={filters} onChange={setFilters} keywords={keywords} />

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-medium">Terjadi kesalahan</p>
          <p className="mt-1">{error}</p>
          <p className="mt-2 text-xs">
            API: <code className="rounded bg-red-100 px-1">{getApiBaseUrl()}</code>
          </p>
        </div>
      )}

      {loading && !overview ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center text-muted-foreground">
          Memuat ringkasan dashboard...
        </div>
      ) : overview ? (
        <>
          {isAcehFocus && (
            <div className="rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Fokus: Bank Indonesia Aceh / KPwBI Aceh
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Mencakup berita & postingan terkait BI Aceh, QRIS Aceh, inflasi Aceh,
                    UMKM Aceh, dan hashtag #BIAceh.
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">
                    {overview.summary.total_mentions}
                  </span>{" "}
                  mentions · {overview.summary.positif_pct}% positif ·{" "}
                  {overview.summary.negatif_pct}% negatif · {overview.summary.netral_pct}%
                  netral
                </p>
              </div>
            </div>
          )}

          <SummaryCards summary={overview.summary} />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <TrendChart data={overview.trend} />
            <PlatformChart data={overview.platforms} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <TopicRanking data={overview.topics} />
            <WordCloud data={overview.word_cloud} />
          </div>

          <PostsTable
            posts={posts?.items || []}
            total={posts?.total || 0}
            page={page}
            pageSize={15}
            loading={loading}
            onPageChange={setPage}
          />

          <SNAGraphPanel data={sna} loading={loading} />
        </>
      ) : null}
    </div>
  );
}
