"""Base connector interface for modular social/news data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class RawPost:
    source: str
    source_post_id: str
    author: Optional[str]
    text_raw: str
    url: Optional[str]
    posted_at: datetime
    keyword_matched: Optional[str] = None


@dataclass
class ConnectorInfo:
    id: str
    name: str
    description: str
    requires_api_key: bool
    configured: bool
    status: str  # connected | not_configured | ready | error
    last_sync: Optional[datetime] = None
    post_count: int = 0


class BaseConnector(ABC):
    """Common interface for all data source connectors."""

    id: str
    name: str
    description: str
    requires_api_key: bool = True

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        ...

    def get_info(self, post_count: int = 0, last_sync: Optional[datetime] = None) -> ConnectorInfo:
        configured = self.is_configured()
        if self.requires_api_key and not configured:
            status = "not_configured"
        elif configured:
            status = "connected" if self.requires_api_key else "ready"
        else:
            status = "ready"
        return ConnectorInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            requires_api_key=self.requires_api_key,
            configured=configured,
            status=status,
            last_sync=last_sync,
            post_count=post_count,
        )
