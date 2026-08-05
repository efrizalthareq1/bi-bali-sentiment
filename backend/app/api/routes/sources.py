"""Data source / connector status endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.connectors import list_connector_status, sync_connector
from app.database import get_db
from app.schemas import ConnectorStatus, IngestResult

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[ConnectorStatus])
def get_sources(db: Session = Depends(get_db)):
    infos = list_connector_status(db)
    return [
        ConnectorStatus(
            name=i.name,
            id=i.id,
            status=i.status,
            description=i.description,
            last_sync=i.last_sync,
            post_count=i.post_count,
            requires_api_key=i.requires_api_key,
            configured=i.configured,
        )
        for i in infos
    ]


@router.post("/{connector_id}/sync", response_model=IngestResult)
def sync_source(connector_id: str, limit: int = 80, db: Session = Depends(get_db)):
    from app.jobs.analyzer import analyze_pending_posts

    try:
        inserted, skipped = sync_connector(db, connector_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gagal sinkronisasi: {exc}") from exc

    analyzed = 0
    if inserted > 0:
        analyzed = analyze_pending_posts(db, batch_size=min(inserted + 20, 100))

    return IngestResult(
        inserted=inserted,
        skipped=skipped,
        message=(
            f"Sinkron {connector_id}: {inserted} baru, {skipped} dilewati"
            + (f", {analyzed} dianalisis." if analyzed else ".")
        ),
    )
