"""SQLAlchemy database engine and session helpers."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    # Railway / Heroku often provide postgres:// — SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


database_url = _normalize_database_url(settings.database_url)

connect_args = {}
if database_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
