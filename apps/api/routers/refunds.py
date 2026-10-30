from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.models import Refund
from payment_lab.db.session import get_db
from payment_lab.domain.models import ApproveRefundRequest, CreateRefundRequest, RefundResponse
from payment_lab.services.refund_service import RefundService

router = APIRouter(tags=["Refunds"])


class RefundListResponse(BaseModel):
    refundable_amount: int
    refunds: List[RefundResponse]


def map_refund_to_response(refund: Refund) -> RefundResponse:
    return RefundResponse(
        id=refund.id,
        public_id=refund.public_id,
        payment_id=refund.payment_id,
        amount=refund.amount,
        currency=refund.currency,
        status=refund.status,
        created_by=refund.created_by,
        approved_by=refund.approved_by,
        provider_reference=refund.provider_reference,
        created_at=refund.created_at,
    )


@router.post("/payments/{payment_id}/refunds", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    payment_id: str,
    payload: CreateRefundRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    created_by: Optional[str] = Header("merchant_user", alias="X-User-ID"),
    scenario: str = Query("success"),
    db: AsyncSession = Depends(get_db),
):
    refund, is_replayed, _ = await RefundService.create_refund(
        session=db,
        payment_identifier=payment_id,
        amount=payload.amount,
        currency_str=payload.currency,
        reason=payload.reason,
        created_by=created_by or "merchant_user",
        idempotency_key_str=idempotency_key,
        provider_scenario=scenario,
    )

    if is_replayed:
        response.headers["Idempotent-Replayed"] = "true"
        response.status_code = status.HTTP_200_OK

    return map_refund_to_response(refund)


@router.get("/payments/{payment_id}/refunds", response_model=RefundListResponse)
async def list_refunds(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
):
    refundable = await RefundService.calculate_refundable_amount(db, payment_id)
    stmt = select(Refund).where(Refund.payment_id == payment_id).order_by(Refund.created_at.desc())
    res = await db.execute(stmt)
    refunds = res.scalars().all()

    return RefundListResponse(
        refundable_amount=refundable,
        refunds=[map_refund_to_response(r) for r in refunds],
    )


@router.post("/refunds/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(
    refund_id: str,
    payload: ApproveRefundRequest,
    db: AsyncSession = Depends(get_db),
):
    refund = await RefundService.approve_refund(
        session=db,
        refund_identifier=refund_id,
        approved_by=payload.approved_by,
    )
    return map_refund_to_response(refund)

