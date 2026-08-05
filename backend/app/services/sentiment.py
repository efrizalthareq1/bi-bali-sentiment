"""Sentiment analysis service: LLM primary, InSet lexicon fallback, with cache."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AnalysisCache
from app.schemas import SentimentResult
from app.services.lexicon import analyze_with_lexicon

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = (
    "Kamu adalah classifier sentimen Bahasa Indonesia. Analisis teks media sosial "
    "berikut terkait Bank Indonesia Provinsi Bali. Balas HANYA dalam format JSON:\n"
    '{{"sentiment": "positif|negatif|netral", "confidence": 0.0-1.0, '
    '"topic_tag": "...", "reasoning": "1 kalimat singkat"}}\n'
    'Teks: "{text}"'
)


def text_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_llm_json(raw: str) -> Optional[dict]:
    raw = raw.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def _call_openai(text: str) -> SentimentResult:
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = CLASSIFIER_PROMPT.format(text=text[:4000])
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
    )
    content = response.choices[0].message.content or ""
    data = _parse_llm_json(content)
    if not data:
        raise ValueError("Failed to parse OpenAI JSON response")
    return SentimentResult(
        sentiment=data["sentiment"],
        confidence=float(data["confidence"]),
        topic_tag=data.get("topic_tag", "umum"),
        reasoning=data.get("reasoning", ""),
        model_used=settings.openai_model,
    )


def _call_anthropic(text: str) -> SentimentResult:
    import httpx

    settings = get_settings()
    prompt = CLASSIFIER_PROMPT.format(text=text[:4000])
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        body = resp.json()
    content = body["content"][0]["text"]
    data = _parse_llm_json(content)
    if not data:
        raise ValueError("Failed to parse Anthropic JSON response")
    return SentimentResult(
        sentiment=data["sentiment"],
        confidence=float(data["confidence"]),
        topic_tag=data.get("topic_tag", "umum"),
        reasoning=data.get("reasoning", ""),
        model_used=settings.anthropic_model,
    )


def _lexicon_result(text: str) -> SentimentResult:
    sentiment, confidence, topic, reasoning = analyze_with_lexicon(text)
    return SentimentResult(
        sentiment=sentiment,
        confidence=confidence,
        topic_tag=topic,
        reasoning=reasoning,
        model_used="inset-lexicon",
    )


def get_cached(db: Session, text: str) -> Optional[SentimentResult]:
    row = db.query(AnalysisCache).filter(AnalysisCache.text_hash == text_hash(text)).first()
    if not row:
        return None
    return SentimentResult(
        sentiment=row.sentiment,
        confidence=row.confidence,
        topic_tag=row.topic_tag or "umum",
        reasoning=row.reasoning or "",
        model_used=row.model_used,
    )


def save_cache(db: Session, text: str, result: SentimentResult) -> None:
    h = text_hash(text)
    existing = db.query(AnalysisCache).filter(AnalysisCache.text_hash == h).first()
    if existing:
        return
    db.add(
        AnalysisCache(
            text_hash=h,
            sentiment=result.sentiment,
            confidence=result.confidence,
            topic_tag=result.topic_tag,
            reasoning=result.reasoning,
            model_used=result.model_used or "unknown",
        )
    )
    db.commit()


def analyze_text(text: str, db: Optional[Session] = None, use_cache: bool = True) -> SentimentResult:
    """Analyze Indonesian text. LLM first, lexicon fallback. Optional DB cache."""
    if use_cache and db is not None:
        cached = get_cached(db, text)
        if cached:
            return cached

    settings = get_settings()
    result: Optional[SentimentResult] = None

    try:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            result = _call_openai(text)
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            result = _call_anthropic(text)
    except Exception as exc:
        logger.warning("LLM analysis failed, falling back to lexicon: %s", exc)

    if result is None:
        result = _lexicon_result(text)

    # Normalize sentiment labels
    label = result.sentiment.lower().strip()
    if label not in {"positif", "negatif", "netral"}:
        mapping = {
            "positive": "positif",
            "negative": "negatif",
            "neutral": "netral",
            "pos": "positif",
            "neg": "negatif",
        }
        result.sentiment = mapping.get(label, "netral")

    if use_cache and db is not None:
        try:
            save_cache(db, text, result)
        except Exception as exc:
            logger.warning("Failed to save analysis cache: %s", exc)

    return result
