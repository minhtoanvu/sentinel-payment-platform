from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.session import get_db
from payment_lab.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Payment & QA Analytics"])


@router.get("/kpis")
async def get_payment_kpis_endpoint(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    FR-DASH-003 / TS-092:
    Provides exact payment KPIs with accompanying SQL definitions.
    """
    return await AnalyticsService.get_payment_kpis(db)

