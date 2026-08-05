"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SOURCE_LABELS } from "@/lib/utils";
import type { DashboardOverview } from "@/lib/api";

export function SummaryCards({ summary }: { summary: DashboardOverview["summary"] }) {
  const items = [
    {
      label: "Total Mentions",
      value: summary.total_mentions.toLocaleString("id-ID"),
      hint: summary.unanalyzed ? `${summary.unanalyzed} belum dianalisis` : "Semua teranalisis",
    },
    {
      label: "Positif",
      value: `${summary.positif_pct}%`,
      hint: `${summary.positif} post`,
      color: "text-positif",
    },
    {
      label: "Negatif",
      value: `${summary.negatif_pct}%`,
      hint: `${summary.negatif} post`,
      color: "text-negatif",
    },
    {
      label: "Netral",
      value: `${summary.netral_pct}%`,
      hint: `${summary.netral} post`,
      color: "text-netral",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="pb-1">
            <CardDescription>{item.label}</CardDescription>
            <CardTitle className={`text-3xl ${item.color || ""}`}>{item.value}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">{item.hint}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function TrendChart({ data }: { data: DashboardOverview["trend"] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Tren Sentimen</CardTitle>
        <CardDescription>Volume sentimen dari waktu ke waktu</CardDescription>
      </CardHeader>
      <CardContent className="h-72">
        {data.length === 0 ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 8,
                  color: "#0f172a",
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="positif" stroke="#0f766e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="negatif" stroke="#dc2626" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="netral" stroke="#64748b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export function PlatformChart({ data }: { data: DashboardOverview["platforms"] }) {
  const chartData = data.map((d) => ({
    ...d,
    label: SOURCE_LABELS[d.source] || d.source,
  }));
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Perbandingan Platform</CardTitle>
        <CardDescription>Jumlah mentions per sumber</CardDescription>
      </CardHeader>
      <CardContent className="h-72">
        {chartData.length === 0 ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 8,
                  color: "#0f172a",
                }}
              />
              <Legend />
              <Bar dataKey="positif" stackId="a" fill="#0f766e" />
              <Bar dataKey="negatif" stackId="a" fill="#dc2626" />
              <Bar dataKey="netral" stackId="a" fill="#94a3b8" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export function TopicRanking({ data }: { data: DashboardOverview["topics"] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Topik Teratas</CardTitle>
        <CardDescription>Topik yang paling banyak dibicarakan</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.length === 0 ? (
          <EmptyChart />
        ) : (
          data.slice(0, 8).map((topic, i) => (
            <div key={topic.topic_tag} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  {i + 1}. {topic.topic_tag}
                </span>
                <span className="text-muted-foreground">{topic.count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary/80"
                  style={{ width: `${(topic.count / max) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export function WordCloud({ data }: { data: DashboardOverview["word_cloud"] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Word Cloud</CardTitle>
        <CardDescription>Kata yang sering muncul dalam percakapan</CardDescription>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <EmptyChart />
        ) : (
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2 py-2">
            {data.slice(0, 40).map((w) => {
              const size = 0.75 + (w.count / max) * 1.35;
              const opacity = 0.45 + (w.count / max) * 0.55;
              return (
                <span
                  key={w.word}
                  title={`${w.word}: ${w.count}`}
                  className="font-display text-primary transition hover:scale-105"
                  style={{ fontSize: `${size}rem`, opacity }}
                >
                  {w.word}
                </span>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-full min-h-32 items-center justify-center text-sm text-muted-foreground">
      Belum ada data untuk filter ini
    </div>
  );
}
