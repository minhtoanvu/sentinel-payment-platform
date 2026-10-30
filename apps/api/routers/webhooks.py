import json
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from payment_lab.core.errors import ValidationError
from payment_lab.db.session import get_db
from payment_lab.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/provider", status_code=status.HTTP_200_OK)
async def receive_provider_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Provider-Signature"),
    timestamp: Optional[str] = Header(None, alias="X-Provider-Timestamp"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    body_bytes = await request.body()
    try:
        payload_dict = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        raise ValidationError("Malformed JSON payload in webhook body")

    result = await WebhookService.process_webhook(
        session=db,
        provider="simulated_provider",
        payload_bytes=body_bytes,
        payload_dict=payload_dict,
        signature_header=signature,
        timestamp_header=timestamp,
    )
    return result

