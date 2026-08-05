"""Build Sentiment Network Analysis graph from posts, keywords, and authors."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models import Post, SentimentScore


CLUSTER_META = {
    "positif": {
        "label": "KLASTER PUBLIK POSITIF",
        "color": "#22c55e",
    },
    "negatif": {
        "label": "KLASTER PUBLIK KRITIS",
        "color": "#ef4444",
    },
    "netral": {
        "label": "KLASTER PUBLIK UMUM",
        "color": "#a1a1aa",
    },
    "media": {
        "label": "KLASTER MEDIA & SUMBER INFORMASI",
        "color": "#60a5fa",
    },
}


def _node_id(kind: str, value: str) -> str:
    safe = value.strip().lower().replace(" ", "_")[:80]
    return f"{kind}:{safe}"


def _dominant_sentiment(counts: Counter) -> str:
    if not counts:
        return "netral"
    return counts.most_common(1)[0][0]


def _cluster_for(node_type: str, sentiment: str) -> str:
    if node_type == "source":
        return "media"
    if sentiment in CLUSTER_META:
        return sentiment
    return "netral"


def _annotation_points(posts: List[Post], sentiment: str, limit: int = 4) -> List[str]:
    topic_counter: Counter = Counter()
    keyword_counter: Counter = Counter()
    for post in posts:
        score = post.sentiment
        if not score or score.sentiment != sentiment:
            continue
        if score.topic_tag:
            topic_counter[score.topic_tag] += 1
        if post.keyword_matched:
            keyword_counter[post.keyword_matched] += 1

    points: List[str] = []
    for topic, n in topic_counter.most_common(3):
        points.append(f"Topik dominan: {topic} ({n})")
    for kw, n in keyword_counter.most_common(2):
        if len(points) >= limit:
            break
        points.append(f"Keyword: {kw} ({n})")
    if not points:
        points = ["Belum ada pola topik yang cukup kuat pada klaster ini."]
    return points[:limit]


def build_sna_graph(
    db: Session,
    *,
    source: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    keyword: Optional[str] = None,
    sentiment: Optional[str] = None,
    q: Optional[str] = None,
    max_nodes: int = 120,
    max_posts: int = 800,
) -> dict:
    query = (
        db.query(Post)
        .outerjoin(SentimentScore)
        .options(joinedload(Post.sentiment))
        .order_by(Post.posted_at.desc())
    )
    if source:
        query = query.filter(Post.source == source)
    if date_from:
        query = query.filter(Post.posted_at >= date_from)
    if date_to:
        query = query.filter(Post.posted_at <= date_to)
    if keyword:
        query = query.filter(Post.keyword_matched.ilike(f"%{keyword}%"))
    if q:
        query = query.filter(Post.text_raw.ilike(f"%{q}%"))
    if sentiment:
        query = query.filter(SentimentScore.sentiment == sentiment)

    posts = query.limit(max_posts).all()
    all_mentions = len(posts)

    author_sent: Dict[str, Counter] = defaultdict(Counter)
    author_count: Counter = Counter()
    author_news: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    keyword_sent: Dict[str, Counter] = defaultdict(Counter)
    keyword_count: Counter = Counter()
    topic_sent: Dict[str, Counter] = defaultdict(Counter)
    topic_count: Counter = Counter()
    source_sent: Dict[str, Counter] = defaultdict(Counter)
    source_count: Counter = Counter()

    edge_weights: Counter = Counter()
    sentiment_totals = Counter()

    for post in posts:
        score = post.sentiment
        sent = (score.sentiment if score else "netral") or "netral"
        sentiment_totals[sent] += 1

        author_label = (post.author or post.source or "unknown").strip() or post.source
        author_key = _node_id("author", author_label)
        author_count[author_key] += 1
        author_sent[author_key][sent] += 1
        author_news[author_key][1] += 1
        if post.source == "news":
            author_news[author_key][0] += 1

        source_key = _node_id("source", post.source)
        source_count[source_key] += 1
        source_sent[source_key][sent] += 1

        kw = (post.keyword_matched or "").strip()
        topic = (score.topic_tag if score and score.topic_tag else "umum").strip()

        if kw:
            kw_key = _node_id("keyword", kw)
            keyword_count[kw_key] += 1
            keyword_sent[kw_key][sent] += 1
            edge_weights[(author_key, kw_key)] += 1
            if topic:
                topic_key = _node_id("topic", topic)
                edge_weights[(kw_key, topic_key)] += 1

        if topic:
            topic_key = _node_id("topic", topic)
            topic_count[topic_key] += 1
            topic_sent[topic_key][sent] += 1
            edge_weights[(author_key, topic_key)] += 1

    candidate_nodes: List[Tuple[str, str, str, int, Counter]] = []
    for aid, cnt in author_count.most_common(80):
        label = aid.split(":", 1)[1].replace("_", " ")
        candidate_nodes.append((aid, label, "author", cnt, author_sent[aid]))
    for kid, cnt in keyword_count.most_common(40):
        label = kid.split(":", 1)[1].replace("_", " ")
        candidate_nodes.append((kid, label, "keyword", cnt, keyword_sent[kid]))
    for tid, cnt in topic_count.most_common(20):
        label = tid.split(":", 1)[1].replace("_", " ")
        candidate_nodes.append((tid, label, "topic", cnt, topic_sent[tid]))
    for sid, cnt in source_count.most_common(10):
        label = sid.split(":", 1)[1]
        candidate_nodes.append((sid, label, "source", cnt, source_sent[sid]))

    candidate_nodes.sort(key=lambda x: x[3], reverse=True)
    selected = candidate_nodes[:max_nodes]
    selected_ids = {n[0] for n in selected}

    nodes = []
    for nid, label, ntype, cnt, sent_c in selected:
        dom = _dominant_sentiment(sent_c)
        cluster = _cluster_for(ntype, dom)
        if ntype == "author":
            news_n, total_n = author_news.get(nid, [0, 0])
            if total_n and news_n / total_n >= 0.6:
                cluster = "media"
            display = label if (" " in label or label.startswith("@")) else f"@{label}"
        else:
            display = label
        nodes.append(
            {
                "id": nid,
                "label": display,
                "type": ntype,
                "sentiment": dom,
                "cluster": cluster,
                "size": cnt,
                "color": CLUSTER_META[cluster]["color"],
            }
        )

    edges = []
    for (a, b), w in edge_weights.most_common(500):
        if a in selected_ids and b in selected_ids and a != b:
            edges.append({"source": a, "target": b, "weight": int(w)})

    n_nodes = len(nodes)
    n_edges = len(edges)
    density = round(100 * (2 * n_edges) / (n_nodes * (n_nodes - 1)), 2) if n_nodes > 1 else 0.0
    avg_degree = round((2 * n_edges) / n_nodes, 1) if n_nodes else 0.0

    analyzed = sum(sentiment_totals.values()) or 1
    sentiments = {
        "positif": sentiment_totals.get("positif", 0),
        "negatif": sentiment_totals.get("negatif", 0),
        "netral": sentiment_totals.get("netral", 0),
        "positif_pct": round(100 * sentiment_totals.get("positif", 0) / analyzed, 1),
        "negatif_pct": round(100 * sentiment_totals.get("negatif", 0) / analyzed, 1),
        "netral_pct": round(100 * sentiment_totals.get("netral", 0) / analyzed, 1),
    }

    clusters = []
    for cid, meta in CLUSTER_META.items():
        cluster_nodes = [n for n in nodes if n["cluster"] == cid]
        if not cluster_nodes:
            continue
        if cid == "media":
            points = [
                "Sumber berita / outlet mendistribusikan isu BI & kebijakan.",
                "Akun informasi menjadi jembatan antara isu dan publik.",
            ]
            top_media = [n["label"] for n in cluster_nodes[:3]]
            if top_media:
                points.insert(0, "Outlet aktif: " + ", ".join(top_media))
        else:
            points = _annotation_points(posts, cid)
        clusters.append(
            {
                "id": cid,
                "label": meta["label"],
                "sentiment": cid,
                "color": meta["color"],
                "node_count": len(cluster_nodes),
                "points": points,
            }
        )

    top_nodes = [
        {
            "id": n["id"],
            "label": n["label"],
            "count": n["size"],
            "type": n["type"],
            "sentiment": n["sentiment"],
            "cluster": n["cluster"],
        }
        for n in sorted(nodes, key=lambda x: x["size"], reverse=True)[:50]
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "stats": {
            "all_mentions": all_mentions,
            "all_sources": len({p.source for p in posts}),
            "nodes": n_nodes,
            "edges": n_edges,
            "density_pct": density,
            "avg_degree": avg_degree,
        },
        "sentiments": sentiments,
        "top_nodes": top_nodes,
    }
