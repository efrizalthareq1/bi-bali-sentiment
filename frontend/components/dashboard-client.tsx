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
import { IgCommentsPanel } from "@/components/ig-comments-panel";
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

export function DashboardClient() {
  const [filters, setFilters] = useState<Filters>({});
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [sna, setSna] = useState<SNAGraph | null>(null);
  const [posts, setPosts] = useState<PostListResponse | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

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

        // API max page_size is 100 — fetch two pages for SNA without failing the dashboard
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

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await api.seed(180);
      await load(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membuat data dummy");
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">
            Dashboard Sentimen
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Gambaran tren persepsi publik terhadap kebijakan dan program Bank Indonesia
            Kantor Perwakilan Provinsi Bali.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void load(page)} disabled={loading}>
            {loading ? "Memuat..." : "Muat ulang"}
          </Button>
          <Button variant="accent" onClick={handleSeed} disabled={seeding}>
            {seeding ? "Menyiapkan..." : "Generate Dummy Data"}
          </Button>
        </div>
      </div>

      <GlobalFilters value={filters} onChange={setFilters} keywords={keywords} />

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-medium">Terjadi kesalahan</p>
          <p className="mt-1">{error}</p>
          <p className="mt-2 text-xs">
            Pastikan backend berjalan di{" "}
            <code className="rounded bg-red-100 px-1 text-red-900">{getApiBaseUrl()}</code>
          </p>
        </div>
      )}

      {loading && !overview ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center text-muted-foreground">
          Memuat ringkasan dashboard...
        </div>
      ) : overview ? (
        <>
          <SummaryCards summary={overview.summary} />
          <IgCommentsPanel />
          <SNAGraphPanel data={sna} loading={loading} />
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
        </>
      ) : null}
    </div>
  );
}
