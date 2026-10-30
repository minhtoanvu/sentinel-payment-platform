from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.db.session import get_db
from payment_lab.domain.models import CreatePaymentRequest, PaymentResponse, PaymentTimelineItem
from payment_lab.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


def map_payment_to_response(payment) -> PaymentResponse:
    timeline = []
    try:
        if hasattr(payment, "status_history") and payment.status_history:
            timeline = [
                PaymentTimelineItem(
                    from_status=h.from_status,
                    to_status=h.to_status,
                    reason=h.reason,
                    actor=h.actor,
                    correlation_id=h.correlation_id,
                    at=h.at,
                )
                for h in sorted(payment.status_history, key=lambda x: x.at)
            ]
    except Exception:
        timeline = []

    return PaymentResponse(
        id=payment.id,
        public_id=payment.public_id,
        merchant_id=payment.merchant_id,
        merchant_reference=payment.merchant_reference,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        refunded_amount=payment.refunded_amount,
        needs_review=payment.needs_review,
        provider_reference=payment.provider_reference,
        expires_at=payment.expires_at,
        succeeded_at=payment.succeeded_at,
        created_at=payment.created_at,
        timeline=timeline,
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: Request,
    response: Response,
    payload: CreatePaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    merchant_id: Optional[str] = Header("m_active_1", alias="X-Merchant-ID"),
    db: AsyncSession = Depends(get_db),
):
    corr_id = getattr(request.state, "correlation_id", None)
    payment, is_replayed = await PaymentService.create_payment(
        session=db,
        merchant_id=merchant_id or "m_active_1",
        amount=payload.amount,
        currency_str=payload.currency,
        merchant_reference=payload.merchant_reference,
        payment_method_id=payload.payment_method_id,
        description=payload.description,
        idempotency_key_str=idempotency_key,
        correlation_id=corr_id,
    )

    if is_replayed:
        response.headers["Idempotent-Replayed"] = "true"
        response.status_code = status.HTTP_200_OK

    return map_payment_to_response(payment)


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    status: Optional[str] = Query(None),
    needs_review: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    merchant_id: Optional[str] = Header("m_active_1", alias="X-Merchant-ID"),
    db: AsyncSession = Depends(get_db),
):
    payments = await PaymentService.list_payments(
        session=db,
        merchant_id=merchant_id,
        status=status,
        needs_review=needs_review,
        limit=limit,
    )
    return [map_payment_to_response(p) for p in payments]


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    merchant_id: Optional[str] = Header("m_active_1", alias="X-Merchant-ID"),
    db: AsyncSession = Depends(get_db),
):
    payment = await PaymentService.get_payment(
        session=db,
        payment_identifier=payment_id,
        merchant_id=merchant_id,
    )
    return map_payment_to_response(payment)


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: str,
    request: Request,
    scenario: str = Query("success"),
    db: AsyncSession = Depends(get_db),
):
    corr_id = getattr(request.state, "correlation_id", None)
    payment = await PaymentService.confirm_payment(
        session=db,
        payment_identifier=payment_id,
        provider_scenario=scenario,
        correlation_id=corr_id,
    )
    return map_payment_to_response(payment)


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    corr_id = getattr(request.state, "correlation_id", None)
    payment = await PaymentService.cancel_payment(
        session=db,
        payment_identifier=payment_id,
        correlation_id=corr_id,
    )
    return map_payment_to_response(payment)
