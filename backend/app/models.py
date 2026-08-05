"""SQLAlchemy ORM models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="umum")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("source", "source_post_id", name="uq_source_post"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_raw: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    keyword_matched: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    sentiment: Mapped[Optional["SentimentScore"]] = relationship(
        "SentimentScore",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    topic_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    post: Mapped["Post"] = relationship("Post", back_populates="sentiment")


class AnalysisCache(Base):
    """Cache sentiment results by text hash to avoid re-analyzing identical content."""

    __tablename__ = "analysis_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    topic_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
