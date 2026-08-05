"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, dashboard, ingest, posts, sources
from app.config import get_settings
from app.database import Base, engine
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.services.dummy_data import seed_keywords
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_keywords(db)
    finally:
        db.close()
    start_scheduler()
    logger.info("BI Bali Sentiment API ready")
    yield
    stop_scheduler()


settings = get_settings()

app = FastAPI(
    title="BI Bali Sentiment Analysis API",
    description="Platform analisis sentimen publik untuk KPwBI Bali",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = settings.cors_origin_list
_allow_credentials = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not _allow_credentials else _cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(posts.router)
app.include_router(dashboard.router)
app.include_router(ingest.router)
app.include_router(sources.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bi-bali-sentiment"}
