"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SentimentBadge } from "@/components/ui/badge";
import { api, type IgCommentSummary } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const USERNAME = "qrissummerrun";

export function IgCommentsPanel() {
  const [data, setData] = useState<IgCommentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await api.igComments(USERNAME);
      setData(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuat komentar IG");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sync = async () => {
    setSyncing(true);
    setMessage(null);
    setError(null);
    try {
      const res = await api.syncIgComments(USERNAME);
      setMessage(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal sync komentar");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border pb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary">
              Instagram Comments
            </p>
            <CardTitle className="mt-1">Sentimen Komentar @{USERNAME}</CardTitle>
            <CardDescription>
              Analisis positif / negatif / netral dari komentar netizen di setiap postingan akun{" "}
              <a
                href={`https://www.instagram.com/${USERNAME}/`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                QRIS Bali Summer Run
                <ExternalLink className="h-3 w-3" />
              </a>
              .
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => void sync()} disabled={syncing}>
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Menarik..." : "Tarik komentar asli"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        {message && (
          <p className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
            {message}
          </p>
        )}
        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}

        {loading && !data ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Memuat ringkasan komentar...</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Total komentar" value={String(data?.total_comments ?? 0)} />
              <Stat
                label="Positif"
                value={`${data?.positif_pct ?? 0}%`}
                hint={`${data?.positif ?? 0} komentar`}
                tone="positif"
              />
              <Stat
                label="Negatif"
                value={`${data?.negatif_pct ?? 0}%`}
                hint={`${data?.negatif ?? 0} komentar`}
                tone="negatif"
              />
              <Stat
                label="Netral"
                value={`${data?.netral_pct ?? 0}%`}
                hint={`${data?.netral ?? 0} komentar`}
                tone="netral"
              />
            </div>

            {(!data || data.total_comments === 0) && (
              <div className="rounded-xl border border-dashed border-border bg-muted/40 px-4 py-5 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Belum ada komentar tersimpan</p>
                <p className="mt-2">
                  Komentar asli hanya bisa ditarik jika backend punya akses ke akun{" "}
                  <strong>@{USERNAME}</strong> via Meta Graph API.
                </p>
                <ol className="mt-2 list-decimal space-y-1 pl-5">
                  <li>
                    Di{" "}
                    <a
                      href="https://developers.facebook.com/"
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary hover:underline"
                    >
                      Meta for Developers
                    </a>
                    , hubungkan Instagram Business <strong>@{USERNAME}</strong>.
                  </li>
                  <li>
                    Set di Railway (service <code>api</code>):{" "}
                    <code>INSTAGRAM_ACCESS_TOKEN</code> dan{" "}
                    <code>INSTAGRAM_BUSINESS_ACCOUNT_ID</code>.
                  </li>
                  <li>
                    Klik <strong>Tarik komentar</strong> — sistem akan mengambil komentar
                    netizen per postingan dan menganalisis sentimennya.
                  </li>
                </ol>
                <p className="mt-3 text-xs">
                  <strong>Opsi B (cookie):</strong> lihat file{" "}
                  <code>TUTORIAL-INSTAGRAM-SESSION.md</code> di folder project. Ringkasnya:
                  login instagram.com → F12 → Application → Cookies → salin{" "}
                  <code>sessionid</code> & <code>csrftoken</code> → set di Railway sebagai{" "}
                  <code>INSTAGRAM_SESSION_ID</code> dan <code>INSTAGRAM_CSRF_TOKEN</code> →
                  klik <strong>Tarik komentar asli</strong>.
                </p>
              </div>
            )}

            {data && data.items.length > 0 && (
              <ul className="divide-y divide-border rounded-xl border border-border">
                {data.items.map((item) => (
                  <li key={item.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">@{item.author || "netizen"}</span>
                        {item.posted_at && <span>· {formatDate(item.posted_at)}</span>}
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-primary hover:underline"
                          >
                            post
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-foreground">{item.text_raw}</p>
                    </div>
                    <SentimentBadge sentiment={item.sentiment} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "positif" | "negatif" | "netral";
}) {
  const color =
    tone === "positif"
      ? "text-positif"
      : tone === "negatif"
        ? "text-negatif"
        : tone === "netral"
          ? "text-netral"
          : "text-foreground";
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${color}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
