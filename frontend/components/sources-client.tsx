"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, CircleAlert, CircleDashed, Hash, RefreshCw, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type ConnectorStatus, type HashtagCatalog } from "@/lib/api";
import { formatDate } from "@/lib/utils";

function statusMeta(status: string) {
  if (status === "connected" || status === "ready") {
    return {
      label: status === "connected" ? "Terhubung" : "Siap",
      className: "bg-teal-100 text-teal-800 ring-1 ring-teal-200",
      icon: CheckCircle2,
    };
  }
  if (status === "not_configured") {
    return {
      label: "Belum dikonfigurasi",
      className: "bg-amber-100 text-amber-900 ring-1 ring-amber-200",
      icon: CircleDashed,
    };
  }
  return {
    label: "Error",
    className: "bg-red-100 text-red-800 ring-1 ring-red-200",
    icon: CircleAlert,
  };
}

export function SourcesClient() {
  const [sources, setSources] = useState<ConnectorStatus[]>([]);
  const [catalog, setCatalog] = useState<HashtagCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [src, tags] = await Promise.all([api.sources(), api.hashtags()]);
      setSources(src);
      setCatalog(tags);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuat sumber data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const sync = async (id: string) => {
    setBusyId(id);
    setMessage(null);
    setError(null);
    try {
      const result =
        id === "news" ? await api.syncNews() : await api.syncSource(id);
      setMessage(result.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sinkronisasi gagal");
    } finally {
      setBusyId(null);
    }
  };

  const onUpload = async (file: File) => {
    setBusyId("manual");
    setMessage(null);
    setError(null);
    try {
      const result = await api.upload(file);
      setMessage(result.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload gagal");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Sumber Data
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Status connector modular. Fase 1: berita RSS & upload manual. Fase 4: API
            media sosial resmi, termasuk pencarian hashtag Instagram.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4" /> Muat ulang
        </Button>
      </div>

      {message && (
        <div className="rounded-xl border border-teal-500/30 bg-teal-500/10 px-4 py-3 text-sm text-teal-200">
          {message}
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Upload Manual</CardTitle>
          <CardDescription>
            Impor CSV/Excel dengan kolom wajib: <code>text_raw</code>, <code>source</code>.
            Opsional: <code>source_post_id</code>, <code>author</code>, <code>url</code>,{" "}
            <code>posted_at</code>, <code>keyword_matched</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file);
            }}
          />
          <Button
            onClick={() => fileRef.current?.click()}
            disabled={busyId === "manual"}
          >
            <Upload className="h-4 w-4" />
            {busyId === "manual" ? "Mengunggah..." : "Pilih File CSV/Excel"}
          </Button>
          <Button
            variant="outline"
            onClick={() => sync("news")}
            disabled={busyId === "news"}
          >
            {busyId === "news" ? "Menarik berita..." : "Tarik Berita Sekarang"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busyId === "resolve-urls"}
            onClick={async () => {
              setBusyId("resolve-urls");
              setMessage(null);
              setError(null);
              try {
                const r = await api.resolveUrls(200);
                setMessage(r.message);
                await load();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Gagal perbaiki URL");
              } finally {
                setBusyId(null);
              }
            }}
          >
            {busyId === "resolve-urls"
              ? "Memperbaiki URL..."
              : "Perbaiki Tautan Berita (Google News)"}
          </Button>
          <Button
            variant="accent"
            onClick={async () => {
              setBusyId("dummy");
              try {
                const r = await api.seed(180);
                setMessage(r.message);
                await load();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Gagal seed");
              } finally {
                setBusyId(null);
              }
            }}
            disabled={busyId === "dummy"}
          >
            {busyId === "dummy" ? "Generating..." : "Generate Dummy (~180 post)"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="h-5 w-5 text-primary" />
            Katalog Hashtag Instagram
          </CardTitle>
          <CardDescription>
            {catalog
              ? `${catalog.total} hashtag di katalog · ${catalog.priority_count} prioritas untuk sync Graph API (batas ~30 unik / 7 hari).`
              : "Memuat katalog hashtag..."}{" "}
            Data asli membutuhkan <code>INSTAGRAM_ACCESS_TOKEN</code> +{" "}
            <code>INSTAGRAM_BUSINESS_ACCOUNT_ID</code>. Tanpa API, gunakan demo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={busyId === "seed-hashtags"}
              onClick={async () => {
                setBusyId("seed-hashtags");
                setMessage(null);
                setError(null);
                try {
                  const r = await api.seedHashtags();
                  setMessage(r.message);
                  await load();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Gagal seed hashtag");
                } finally {
                  setBusyId(null);
                }
              }}
            >
              {busyId === "seed-hashtags" ? "Menyimpan..." : "Seed Katalog Hashtag"}
            </Button>
            <Button
              size="sm"
              variant="accent"
              disabled={busyId === "ig-demo"}
              onClick={async () => {
                setBusyId("ig-demo");
                setMessage(null);
                setError(null);
                try {
                  const r = await api.instagramDemo(3, true);
                  setMessage(r.message);
                  await load();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Gagal demo IG");
                } finally {
                  setBusyId(null);
                }
              }}
            >
              {busyId === "ig-demo"
                ? "Membuat demo..."
                : "Demo Post IG (30 hashtag prioritas)"}
            </Button>
            <Button
              size="sm"
              disabled={busyId === "instagram"}
              onClick={() => sync("instagram")}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {busyId === "instagram"
                ? "Sync Graph API..."
                : "Sync Hashtag Asli (Graph API)"}
            </Button>
          </div>

          {catalog && (
            <div className="space-y-4">
              {catalog.groups.map((group) => (
                <div key={group.category}>
                  <p className="mb-2 text-sm font-semibold text-foreground">
                    {group.label}{" "}
                    <span className="font-normal text-muted-foreground">
                      ({group.hashtags.length})
                    </span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {group.hashtags.map((tag) => (
                      <Badge
                        key={tag}
                        className="bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30"
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>X, YouTube & Threads (konten asli)</CardTitle>
          <CardDescription>
            Sinkronisasi menghapus data demo palsu, lalu menarik konten publik asli:
            akun <code>@bank_indonesia</code> / mention X, video channel resmi Bank
            Indonesia di YouTube, dan post Threads yang terindeks.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={busyId === "purge"}
            variant="outline"
            onClick={async () => {
              setBusyId("purge");
              setMessage(null);
              setError(null);
              try {
                const r = await api.purgeDemos();
                setMessage(r.message);
                await load();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Gagal hapus demo");
              } finally {
                setBusyId(null);
              }
            }}
          >
            {busyId === "purge" ? "Menghapus..." : "Hapus Data Demo Palsu"}
          </Button>
          <Button size="sm" disabled={busyId === "x"} onClick={() => sync("x")}>
            <RefreshCw className="h-3.5 w-3.5" />
            {busyId === "x" ? "Sync X..." : "Sync X Akun Asli"}
          </Button>
          <Button
            size="sm"
            disabled={busyId === "youtube"}
            onClick={() => sync("youtube")}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {busyId === "youtube" ? "Sync YouTube..." : "Sync YouTube Video Asli"}
          </Button>
          <Button
            size="sm"
            disabled={busyId === "threads"}
            onClick={() => sync("threads")}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {busyId === "threads" ? "Sync Threads..." : "Sync Threads Asli"}
          </Button>
          <Button
            size="sm"
            variant="accent"
            disabled={busyId === "tt-demo"}
            onClick={async () => {
              setBusyId("tt-demo");
              setMessage(null);
              setError(null);
              try {
                const r = await api.tiktokDemo(60);
                setMessage(r.message);
                await load();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Gagal demo TikTok");
              } finally {
                setBusyId(null);
              }
            }}
          >
            {busyId === "tt-demo" ? "Membuat demo..." : "Demo Post TikTok (~60)"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busyId === "tiktok"}
            onClick={() => sync("tiktok")}
          >
            {busyId === "tiktok" ? "Sync TikTok API..." : "Sync TikTok Research API"}
          </Button>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-muted-foreground">Memuat status connector...</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {sources.map((src) => {
            const meta = statusMeta(src.status);
            const Icon = meta.icon;
            const canSync =
              ["news", "x", "instagram", "tiktok", "youtube", "threads"].includes(src.id) &&
              (src.status === "ready" || src.status === "connected");
            return (
              <Card key={src.id}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-xl">{src.name}</CardTitle>
                      <CardDescription className="mt-1">{src.description}</CardDescription>
                    </div>
                    <Badge className={meta.className}>
                      <Icon className="mr-1 h-3.5 w-3.5" />
                      {meta.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                    <div>
                      <p className="text-xs uppercase tracking-wide">Post tersimpan</p>
                      <p className="text-lg font-semibold text-foreground">
                        {src.post_count.toLocaleString("id-ID")}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide">API Key</p>
                      <p className="text-foreground">
                        {src.requires_api_key
                          ? src.configured
                            ? "Sudah diisi"
                            : "Belum diisi"
                          : "Tidak perlu"}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs uppercase tracking-wide">Sinkron terakhir</p>
                      <p className="text-foreground">
                        {src.last_sync ? formatDate(src.last_sync) : "Belum pernah"}
                      </p>
                    </div>
                  </div>
                  {canSync && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busyId === src.id}
                      onClick={() => sync(src.id)}
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      {busyId === src.id ? "Menyinkronkan..." : "Sinkronkan"}
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
