/** Client-side Sentiment Network Analysis builder from posts. */

export type SNAPostLike = {
  id: number;
  source: string;
  author?: string | null;
  keyword_matched?: string | null;
  sentiment?: { sentiment: string; topic_tag?: string | null } | null;
};

export type SNANode = {
  id: string;
  label: string;
  type: string;
  sentiment: string;
  cluster: string;
  size: number;
  color: string;
};

export type SNAGraph = {
  nodes: SNANode[];
  edges: Array<{ source: string; target: string; weight: number }>;
  clusters: Array<{
    id: string;
    label: string;
    sentiment: string;
    color: string;
    node_count: number;
    points: string[];
  }>;
  stats: {
    all_mentions: number;
    all_sources: number;
    nodes: number;
    edges: number;
    density_pct: number;
    avg_degree: number;
  };
  sentiments: {
    positif: number;
    negatif: number;
    netral: number;
    positif_pct: number;
    negatif_pct: number;
    netral_pct: number;
  };
  top_nodes: Array<{
    id: string;
    label: string;
    count: number;
    type: string;
    sentiment: string;
    cluster: string;
  }>;
};

const CLUSTER_META: Record<string, { label: string; color: string }> = {
  positif: { label: "KLASTER PUBLIK POSITIF", color: "#22c55e" },
  negatif: { label: "KLASTER PUBLIK KRITIS", color: "#ef4444" },
  netral: { label: "KLASTER PUBLIK UMUM", color: "#a1a1aa" },
  media: { label: "KLASTER MEDIA & SUMBER INFORMASI", color: "#60a5fa" },
};

function nodeId(kind: string, value: string) {
  return `${kind}:${value.trim().toLowerCase().replace(/\s+/g, "_").slice(0, 80)}`;
}

function dominant(counts: Record<string, number>) {
  const entries = Object.entries(counts);
  if (!entries.length) return "netral";
  entries.sort((a, b) => b[1] - a[1]);
  return entries[0][0];
}

function bump(map: Record<string, Record<string, number>>, key: string, sent: string) {
  if (!map[key]) map[key] = {};
  map[key][sent] = (map[key][sent] || 0) + 1;
}

export function buildSnaFromPosts(posts: SNAPostLike[], maxNodes = 120): SNAGraph {
  const authorCount: Record<string, number> = {};
  const keywordCount: Record<string, number> = {};
  const topicCount: Record<string, number> = {};
  const sourceCount: Record<string, number> = {};
  const authorSent: Record<string, Record<string, number>> = {};
  const keywordSent: Record<string, Record<string, number>> = {};
  const topicSent: Record<string, Record<string, number>> = {};
  const sourceSent: Record<string, Record<string, number>> = {};
  const authorNews: Record<string, [number, number]> = {};
  const edgeWeights: Record<string, number> = {};
  const sentimentTotals: Record<string, number> = { positif: 0, negatif: 0, netral: 0 };
  const labels: Record<string, string> = {};

  const addEdge = (a: string, b: string) => {
    if (a === b) return;
    const key = a < b ? `${a}||${b}` : `${b}||${a}`;
    edgeWeights[key] = (edgeWeights[key] || 0) + 1;
  };

  for (const post of posts) {
    const sent = post.sentiment?.sentiment || "netral";
    sentimentTotals[sent] = (sentimentTotals[sent] || 0) + 1;

    const authorLabel = (post.author || post.source || "unknown").trim();
    const authorKey = nodeId("author", authorLabel);
    labels[authorKey] = authorLabel;
    authorCount[authorKey] = (authorCount[authorKey] || 0) + 1;
    bump(authorSent, authorKey, sent);
    if (!authorNews[authorKey]) authorNews[authorKey] = [0, 0];
    authorNews[authorKey][1] += 1;
    if (post.source === "news") authorNews[authorKey][0] += 1;

    const sourceKey = nodeId("source", post.source);
    labels[sourceKey] = post.source;
    sourceCount[sourceKey] = (sourceCount[sourceKey] || 0) + 1;
    bump(sourceSent, sourceKey, sent);

    const kw = (post.keyword_matched || "").trim();
    const topic = (post.sentiment?.topic_tag || "umum").trim();

    if (kw) {
      const kwKey = nodeId("keyword", kw);
      labels[kwKey] = kw;
      keywordCount[kwKey] = (keywordCount[kwKey] || 0) + 1;
      bump(keywordSent, kwKey, sent);
      addEdge(authorKey, kwKey);
      if (topic) {
        const topicKey = nodeId("topic", topic);
        labels[topicKey] = topic;
        addEdge(kwKey, topicKey);
      }
    }
    if (topic) {
      const topicKey = nodeId("topic", topic);
      labels[topicKey] = topic;
      topicCount[topicKey] = (topicCount[topicKey] || 0) + 1;
      bump(topicSent, topicKey, sent);
      addEdge(authorKey, topicKey);
    }
  }

  type Cand = { id: string; label: string; type: string; count: number; sent: Record<string, number> };
  const candidates: Cand[] = [];
  Object.entries(authorCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 80)
    .forEach(([id, count]) =>
      candidates.push({ id, label: labels[id], type: "author", count, sent: authorSent[id] || {} })
    );
  Object.entries(keywordCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 40)
    .forEach(([id, count]) =>
      candidates.push({ id, label: labels[id], type: "keyword", count, sent: keywordSent[id] || {} })
    );
  Object.entries(topicCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .forEach(([id, count]) =>
      candidates.push({ id, label: labels[id], type: "topic", count, sent: topicSent[id] || {} })
    );
  Object.entries(sourceCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([id, count]) =>
      candidates.push({ id, label: labels[id], type: "source", count, sent: sourceSent[id] || {} })
    );

  candidates.sort((a, b) => b.count - a.count);
  const selected = candidates.slice(0, maxNodes);
  const selectedIds = new Set(selected.map((c) => c.id));

  const nodes: SNANode[] = selected.map((c) => {
    const dom = dominant(c.sent);
    let cluster = c.type === "source" ? "media" : dom;
    if (c.type === "author") {
      const [newsN, totalN] = authorNews[c.id] || [0, 0];
      if (totalN && newsN / totalN >= 0.6) cluster = "media";
    }
    const display =
      c.type === "author" && !c.label.includes(" ") && !c.label.startsWith("@")
        ? `@${c.label}`
        : c.label;
    return {
      id: c.id,
      label: display,
      type: c.type,
      sentiment: dom,
      cluster,
      size: c.count,
      color: CLUSTER_META[cluster]?.color || "#a1a1aa",
    };
  });

  const edges = Object.entries(edgeWeights)
    .map(([key, weight]) => {
      const [source, target] = key.split("||");
      return { source, target, weight };
    })
    .filter((e) => selectedIds.has(e.source) && selectedIds.has(e.target))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 500);

  const nNodes = nodes.length;
  const nEdges = edges.length;
  const density =
    nNodes > 1 ? Math.round((1000 * (2 * nEdges)) / (nNodes * (nNodes - 1))) / 10 : 0;
  const avgDegree = nNodes ? Math.round(((2 * nEdges) / nNodes) * 10) / 10 : 0;
  const analyzed =
    (sentimentTotals.positif || 0) +
      (sentimentTotals.negatif || 0) +
      (sentimentTotals.netral || 0) || 1;

  const topicBySent: Record<string, Record<string, number>> = {};
  const kwBySent: Record<string, Record<string, number>> = {};
  for (const post of posts) {
    const sent = post.sentiment?.sentiment || "netral";
    const topic = post.sentiment?.topic_tag;
    const kw = post.keyword_matched;
    if (topic) {
      if (!topicBySent[sent]) topicBySent[sent] = {};
      topicBySent[sent][topic] = (topicBySent[sent][topic] || 0) + 1;
    }
    if (kw) {
      if (!kwBySent[sent]) kwBySent[sent] = {};
      kwBySent[sent][kw] = (kwBySent[sent][kw] || 0) + 1;
    }
  }

  const clusters = Object.entries(CLUSTER_META)
    .map(([id, meta]) => {
      const clusterNodes = nodes.filter((n) => n.cluster === id);
      if (!clusterNodes.length) return null;
      let points: string[] = [];
      if (id === "media") {
        points = [
          "Sumber berita / outlet mendistribusikan isu BI & kebijakan.",
          "Akun informasi menjadi jembatan antara isu dan publik.",
        ];
        const top = clusterNodes.slice(0, 3).map((n) => n.label);
        if (top.length) points.unshift(`Outlet aktif: ${top.join(", ")}`);
      } else {
        const topics = Object.entries(topicBySent[id] || {})
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3);
        const kws = Object.entries(kwBySent[id] || {})
          .sort((a, b) => b[1] - a[1])
          .slice(0, 2);
        points = [
          ...topics.map(([t, n]) => `Topik dominan: ${t} (${n})`),
          ...kws.map(([k, n]) => `Keyword: ${k} (${n})`),
        ];
        if (!points.length) points = ["Belum ada pola topik yang cukup kuat pada klaster ini."];
      }
      return {
        id,
        label: meta.label,
        sentiment: id,
        color: meta.color,
        node_count: clusterNodes.length,
        points: points.slice(0, 4),
      };
    })
    .filter(Boolean) as SNAGraph["clusters"];

  const top_nodes = [...nodes]
    .sort((a, b) => b.size - a.size)
    .slice(0, 50)
    .map((n) => ({
      id: n.id,
      label: n.label,
      count: n.size,
      type: n.type,
      sentiment: n.sentiment,
      cluster: n.cluster,
    }));

  return {
    nodes,
    edges,
    clusters,
    stats: {
      all_mentions: posts.length,
      all_sources: new Set(posts.map((p) => p.source)).size,
      nodes: nNodes,
      edges: nEdges,
      density_pct: density,
      avg_degree: avgDegree,
    },
    sentiments: {
      positif: sentimentTotals.positif || 0,
      negatif: sentimentTotals.negatif || 0,
      netral: sentimentTotals.netral || 0,
      positif_pct: Math.round((1000 * (sentimentTotals.positif || 0)) / analyzed) / 10,
      negatif_pct: Math.round((1000 * (sentimentTotals.negatif || 0)) / analyzed) / 10,
      netral_pct: Math.round((1000 * (sentimentTotals.netral || 0)) / analyzed) / 10,
    },
    top_nodes,
  };
}
