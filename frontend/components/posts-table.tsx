"use client";

import { useState } from "react";
import { ExternalLink, X } from "lucide-react";
import { SentimentBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getPostOpenUrl,
  isPlaceholderSourceUrl,
  type PostOut,
} from "@/lib/api";
import { SOURCE_LABELS, formatDate } from "@/lib/utils";

type Props = {
  posts: PostOut[];
  total: number;
  page: number;
  pageSize: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
};

export function PostsTable({
  posts,
  total,
  page,
  pageSize,
  loading,
  onPageChange,
}: Props) {
  const [selected, setSelected] = useState<PostOut | null>(null);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Daftar Post</CardTitle>
          <p className="text-sm text-muted-foreground">
            {total.toLocaleString("id-ID")} hasil
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {loading ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Memuat data...</p>
          ) : posts.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Tidak ada post untuk filter ini
            </p>
          ) : (
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="pb-3 pr-3 font-medium">Waktu</th>
                  <th className="pb-3 pr-3 font-medium">Platform</th>
                  <th className="pb-3 pr-3 font-medium">Teks</th>
                  <th className="pb-3 pr-3 font-medium">Keyword</th>
                  <th className="pb-3 pr-3 font-medium">Sentimen</th>
                  <th className="pb-3 font-medium">Topik</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post) => (
                  <tr
                    key={post.id}
                    className="cursor-pointer border-b border-border/70 transition hover:bg-muted/60"
                    onClick={() => setSelected(post)}
                  >
                    <td className="py-3 pr-3 whitespace-nowrap text-xs text-muted-foreground">
                      {formatDate(post.posted_at)}
                    </td>
                    <td className="py-3 pr-3 whitespace-nowrap">
                      {SOURCE_LABELS[post.source] || post.source}
                    </td>
                    <td className="py-3 pr-3 max-w-md">
                      <p className="line-clamp-2">{post.text_raw}</p>
                      {post.author && (
                        <p className="mt-1 text-xs text-muted-foreground">@{post.author}</p>
                      )}
                    </td>
                    <td className="py-3 pr-3 whitespace-nowrap text-xs">
                      {post.keyword_matched ? (
                        <span className="rounded-md bg-muted px-2 py-1 text-foreground">
                          {post.keyword_matched}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="py-3 pr-3">
                      <SentimentBadge sentiment={post.sentiment?.sentiment} />
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {post.sentiment?.topic_tag || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Halaman {page} dari {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >
                Sebelumnya
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => onPageChange(page + 1)}
              >
                Berikutnya
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center"
          onClick={() => setSelected(null)}
        >
          <div
            className="max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-border bg-card p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Detail Post
                </p>
                <h3 className="font-display text-xl font-semibold">
                  {SOURCE_LABELS[selected.source] || selected.source}
                </h3>
              </div>
              <button
                type="button"
                className="rounded-lg p-2 hover:bg-muted"
                onClick={() => setSelected(null)}
                aria-label="Tutup"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mb-4 whitespace-pre-wrap text-sm leading-relaxed">
              {selected.text_raw}
            </p>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Penulis</dt>
                <dd>{selected.author || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Waktu</dt>
                <dd>{formatDate(selected.posted_at)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Keyword</dt>
                <dd>{selected.keyword_matched || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Sentimen</dt>
                <dd>
                  <SentimentBadge sentiment={selected.sentiment?.sentiment} />
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Confidence</dt>
                <dd>
                  {selected.sentiment
                    ? `${Math.round(selected.sentiment.confidence * 100)}%`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Topik</dt>
                <dd>{selected.sentiment?.topic_tag || "—"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted-foreground">Alasan</dt>
                <dd>{selected.sentiment?.reasoning || "—"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted-foreground">Model</dt>
                <dd>{selected.sentiment?.model_used || "—"}</dd>
              </div>
            </dl>
            {selected.url && !isPlaceholderSourceUrl(selected.url) ? (
              <a
                href={getPostOpenUrl(selected.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm text-primary hover:underline"
              >
                Buka sumber asli <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : (
              <p className="mt-5 text-xs text-muted-foreground">
                Tautan sumber tidak tersedia
                {isPlaceholderSourceUrl(selected.url)
                  ? " (data demo/sintetis)."
                  : "."}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
