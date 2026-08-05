"""Pydantic request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SentimentResult(BaseModel):
    sentiment: str = Field(..., pattern="^(positif|negatif|netral)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    topic_tag: str
    reasoning: str
    model_used: Optional[str] = None


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)


class KeywordOut(BaseModel):
    id: int
    keyword: str
    category: str
    active: bool

    model_config = {"from_attributes": True}


class KeywordCreate(BaseModel):
    keyword: str
    category: str = "umum"
    active: bool = True


class SentimentOut(BaseModel):
    sentiment: str
    confidence: float
    topic_tag: Optional[str] = None
    reasoning: Optional[str] = None
    model_used: str
    analyzed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: int
    source: str
    source_post_id: str
    author: Optional[str] = None
    text_raw: str
    url: Optional[str] = None
    posted_at: datetime
    keyword_matched: Optional[str] = None
    sentiment: Optional[SentimentOut] = None

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PostOut]


class SummaryStats(BaseModel):
    total_mentions: int
    positif: int
    negatif: int
    netral: int
    positif_pct: float
    negatif_pct: float
    netral_pct: float
    unanalyzed: int


class TrendPoint(BaseModel):
    date: str
    positif: int
    negatif: int
    netral: int
    total: int


class PlatformStat(BaseModel):
    source: str
    count: int
    positif: int
    negatif: int
    netral: int


class TopicStat(BaseModel):
    topic_tag: str
    count: int
    positif: int
    negatif: int
    netral: int


class WordFreq(BaseModel):
    word: str
    count: int


class SNANode(BaseModel):
    id: str
    label: str
    type: str
    sentiment: str
    cluster: str
    size: int
    color: str


class SNAEdge(BaseModel):
    source: str
    target: str
    weight: int


class SNACluster(BaseModel):
    id: str
    label: str
    sentiment: str
    color: str
    node_count: int
    points: List[str]


class SNAStats(BaseModel):
    all_mentions: int
    all_sources: int
    nodes: int
    edges: int
    density_pct: float
    avg_degree: float


class SNASentiments(BaseModel):
    positif: int
    negatif: int
    netral: int
    positif_pct: float
    negatif_pct: float
    netral_pct: float


class SNATopNode(BaseModel):
    id: str
    label: str
    count: int
    type: str
    sentiment: str
    cluster: str


class SNAGraph(BaseModel):
    nodes: List[SNANode]
    edges: List[SNAEdge]
    clusters: List[SNACluster]
    stats: SNAStats
    sentiments: SNASentiments
    top_nodes: List[SNATopNode]


class DashboardOverview(BaseModel):
    summary: SummaryStats
    trend: List[TrendPoint]
    platforms: List[PlatformStat]
    topics: List[TopicStat]
    word_cloud: List[WordFreq]


class ConnectorStatus(BaseModel):
    name: str
    id: str
    status: str  # connected | not_configured | error | ready
    description: str
    last_sync: Optional[datetime] = None
    post_count: int = 0
    requires_api_key: bool = False
    configured: bool = False


class IngestResult(BaseModel):
    inserted: int
    skipped: int
    message: str


class SeedResult(BaseModel):
    posts_created: int
    keywords_created: int
    analyzed: int
    message: str


class HashtagGroup(BaseModel):
    category: str
    label: str
    hashtags: List[str]


class HashtagCatalog(BaseModel):
    total: int
    priority_count: int
    groups: List[HashtagGroup]


class IgCommentItem(BaseModel):
    id: int
    author: Optional[str] = None
    text_raw: str
    url: Optional[str] = None
    posted_at: Optional[str] = None
    sentiment: Optional[str] = None
    confidence: Optional[float] = None


class IgCommentDiagnostic(BaseModel):
    username: str
    session_configured: bool
    session_id_length: int
    csrf_configured: bool
    ds_user_id_configured: bool
    graph_api_configured: bool
    profile_status: Optional[int] = None
    profile_message: str = ""
    media_posts_found: int = 0
    comments_status: Optional[int] = None
    comments_found_sample: int = 0
    ok: bool = False
    hint: str = ""


class IgCommentSummary(BaseModel):
    username: str
    profile_url: str
    total_comments: int
    positif: int
    negatif: int
    netral: int
    unanalyzed: int
    positif_pct: float
    negatif_pct: float
    netral_pct: float
    items: List[IgCommentItem]
