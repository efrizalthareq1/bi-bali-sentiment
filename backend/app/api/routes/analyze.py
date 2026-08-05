"""API route: sentiment analysis."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AnalyzeRequest, SentimentResult
from app.services.sentiment import analyze_text

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=SentimentResult)
def analyze_endpoint(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    return analyze_text(payload.text, db=db, use_cache=True)
