"""Analysis history API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import AnalysisHistory, HistoryResponse, User

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistoryResponse])
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's analysis history, newest first (without full report)."""
    result = await db.execute(
        select(AnalysisHistory)
        .where(AnalysisHistory.user_id == user.id)
        .order_by(desc(AnalysisHistory.created_at))
        .limit(50)
    )
    items = result.scalars().all()
    # Exclude report_json from list response to keep it lightweight
    return [
        HistoryResponse(
            id=item.id,
            wokwi_url=item.wokwi_url,
            project_id=item.project_id,
            summary_json=item.summary_json,
            fault_count=item.fault_count,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.get("/{history_id}", response_model=HistoryResponse)
async def get_history_item(
    history_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single history entry with the full report."""
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id,
            AnalysisHistory.user_id == user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found")
    return entry


@router.delete("/{history_id}")
async def delete_history_item(
    history_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a history entry (only if it belongs to the current user)."""
    result = await db.execute(
        select(AnalysisHistory).where(
            AnalysisHistory.id == history_id,
            AnalysisHistory.user_id == user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found")

    await db.delete(entry)
    await db.commit()
    return {"message": "Deleted"}
