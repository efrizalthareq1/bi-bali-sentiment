const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiBaseUrl() {
  return API_URL;
}

export function getPostOpenUrl(postId: number) {
  return `${API_URL}/posts/${postId}/open`;
}

export function isPlaceholderSourceUrl(url?: string | null) {
  if (!url) return true;
  const u = url.toLowerCase();
  return (
    u.includes("example.com") ||
    u.includes("/demo-") ||
    u.includes("ig-demo-") ||
    u.includes("tt-demo-") ||
    u.includes("dummy-") ||
    u.includes("watch?v=demo") ||
    u.includes("/post/demo")
  );
}

export type Filters = {
  source?: string;
  sentiment?: string;
  keyword?: string;
  date_from?: string;
  date_to?: string;
  q?: string;
  topic?: string;
};

function toQuery(filters: Filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) params.set(k, v);
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Permintaan gagal");
  }
  return res.json() as Promise<T>;
}

export type SummaryStats = {
  total_mentions: number;
  positif: number;
  negatif: number;
  netral: number;
  positif_pct: number;
  negatif_pct: number;
  netral_pct: number;
  unanalyzed: number;
};

export type WordFreq = { word: string; count: number };

export type DashboardOverview = {
  summary: SummaryStats;
  trend: Array<{
    date: string;
    positif: number;
    negatif: number;
    netral: number;
    total: number;
  }>;
  platforms: Array<{
    source: string;
    count: number;
    positif: number;
    negatif: number;
    netral: number;
  }>;
  topics: Array<{
    topic_tag: string;
    count: number;
    positif: number;
    negatif: number;
    netral: number;
  }>;
  word_cloud: WordFreq[];
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

export type SentimentOut = {
  sentiment: string;
  confidence: number;
  topic_tag?: string;
  reasoning?: string;
  model_used: string;
  analyzed_at?: string;
};

export type PostOut = {
  id: number;
  source: string;
  source_post_id: string;
  author?: string;
  text_raw: string;
  url?: string;
  posted_at: string;
  keyword_matched?: string;
  sentiment?: SentimentOut;
};

export type PostListResponse = {
  total: number;
  page: number;
  page_size: number;
  items: PostOut[];
};

export type ConnectorStatus = {
  name: string;
  id: string;
  status: string;
  description: string;
  last_sync?: string;
  post_count: number;
  requires_api_key: boolean;
  configured: boolean;
};

export type KeywordOut = {
  id: number;
  keyword: string;
  category: string;
  active: boolean;
};

export type HashtagCatalog = {
  total: number;
  priority_count: number;
  groups: Array<{
    category: string;
    label: string;
    hashtags: string[];
  }>;
};

function buildQuery(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") search.set(k, String(v));
  });
  const s = search.toString();
  return s ? `?${s}` : "";
}

export type IgCommentItem = {
  id: number;
  author?: string;
  text_raw: string;
  url?: string;
  posted_at?: string;
  sentiment?: string;
  confidence?: number;
};

export type IgCommentSummary = {
  username: string;
  profile_url: string;
  total_comments: number;
  positif: number;
  negatif: number;
  netral: number;
  unanalyzed: number;
  positif_pct: number;
  negatif_pct: number;
  netral_pct: number;
  items: IgCommentItem[];
};

export const api = {
  overview: (filters?: Filters) =>
    request<DashboardOverview>(`/dashboard/overview${toQuery(filters)}`),
  sna: (filters?: Filters) =>
    request<SNAGraph>(`/dashboard/sna${toQuery(filters)}`),
  posts: (filters: Filters & { page?: number; page_size?: number } = {}) => {
    const { page = 1, page_size = 20, ...rest } = filters;
    return request<PostListResponse>(
      `/posts${buildQuery({ ...rest, page, page_size })}`
    );
  },
  post: (id: number) => request<PostOut>(`/posts/${id}`),
  sources: () => request<ConnectorStatus[]>("/sources"),
  keywords: () => request<KeywordOut[]>("/keywords"),
  hashtags: () => request<HashtagCatalog>("/hashtags"),
  seed: (count = 180) =>
    request<{ posts_created: number; analyzed: number; message: string }>(
      `/ingest/seed?count=${count}`,
      { method: "POST" }
    ),
  seedHashtags: () =>
    request<{ keywords_created: number; message: string }>("/ingest/seed-hashtags", {
      method: "POST",
    }),
  instagramDemo: (perHashtag = 3, priorityOnly = true) =>
    request<{ posts_created: number; analyzed: number; message: string }>(
      `/ingest/instagram-demo?per_hashtag=${perHashtag}&priority_only=${priorityOnly}`,
      { method: "POST" }
    ),
  tiktokDemo: (count = 60) =>
    request<{ posts_created: number; analyzed: number; message: string }>(
      `/ingest/tiktok-demo?count=${count}`,
      { method: "POST" }
    ),
  outlookDemo: (count = 40) =>
    request<{ posts_created: number; analyzed: number; message: string }>(
      `/ingest/outlook-demo?count=${count}`,
      { method: "POST" }
    ),
  syncNews: () =>
    request<{ inserted: number; skipped: number; message: string }>("/ingest/news", {
      method: "POST",
    }),
  syncSource: (id: string) =>
    request<{ inserted: number; skipped: number; message: string }>(
      `/sources/${id}/sync`,
      { method: "POST" }
    ),
  upload: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ inserted: number; skipped: number; message: string }>(
      "/ingest/upload",
      { method: "POST", body: form }
    );
  },
  analyzePending: () =>
    request<{ inserted: number; message: string }>("/ingest/analyze-pending", {
      method: "POST",
    }),
  resolveUrls: (limit = 200) =>
    request<{ inserted: number; skipped: number; message: string }>(
      `/posts/resolve-urls?limit=${limit}`,
      { method: "POST" }
    ),
  purgeDemos: () =>
    request<{ inserted: number; skipped: number; message: string }>(
      "/ingest/purge-demos",
      { method: "POST" }
    ),
  syncIgComments: (username = "qrissummerrun") =>
    request<{ inserted: number; skipped: number; message: string }>(
      `/ingest/instagram-comments?username=${encodeURIComponent(username)}`,
      { method: "POST" }
    ),
  igComments: (username = "qrissummerrun") =>
    request<IgCommentSummary>(
      `/dashboard/instagram-comments?username=${encodeURIComponent(username)}`
    ),
  uploadIgComments: async (file: File, username = "qrissummerrun") => {
    const form = new FormData();
    form.append("file", file);
    return request<{ inserted: number; skipped: number; message: string }>(
      `/ingest/instagram-comments/upload?username=${encodeURIComponent(username)}`,
      { method: "POST", body: form }
    );
  },
};
