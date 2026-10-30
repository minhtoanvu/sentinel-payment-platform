import hashlib
import hmac
import time
import uuid
from typing import Any, Optional
from pydantic import BaseModel
from payment_lab.core.config import settings


class ProviderChargeResult(BaseModel):
    outcome: str  # SUCCESS, DECLINE, TIMEOUT
    provider_reference: str
    failure_code: Optional[str] = None


class ProviderStatusResult(BaseModel):
    status: str  # SUCCEEDED, FAILED, UNKNOWN
    provider_reference: str


class ProviderRefundResult(BaseModel):
    outcome: str  # SUCCESS, DECLINE, TIMEOUT
    provider_reference: str
    failure_code: Optional[str] = None


class ProviderSimulatorException(Exception):
    pass


class ProviderTimeoutException(ProviderSimulatorException):
    """Simulated network timeout from provider."""
    def __init__(self, provider_reference: str, message: str = "Provider gateway timed out"):
        super().__init__(message)
        self.provider_reference = provider_reference


class ProviderSimulator:
    def __init__(self, secret: str = settings.WEBHOOK_SECRET):
        self.secret = secret
        # In-memory record of provider transactions for query_status
        self._provider_store: dict[str, str] = {}
        # Count charges per payment to verify INV-04
        self._charge_counts: dict[str, int] = {}

    def get_charge_count(self, payment_id: str) -> int:
        return self._charge_counts.get(payment_id, 0)

    async def charge(
        self,
        payment_id: str,
        amount: int,
        currency: str,
        scenario: str = "success",
    ) -> ProviderChargeResult:
        """Simulate charge to upstream provider."""
        provider_ref = f"sim_ch_{uuid.uuid4().hex[:16]}"
        self._charge_counts[payment_id] = self._charge_counts.get(payment_id, 0) + 1

        if scenario == "success":
            self._provider_store[provider_ref] = "SUCCEEDED"
            return ProviderChargeResult(outcome="SUCCESS", provider_reference=provider_ref)

        elif scenario == "decline":
            self._provider_store[provider_ref] = "FAILED"
            return ProviderChargeResult(
                outcome="DECLINE",
                provider_reference=provider_ref,
                failure_code="CARD_DECLINED",
            )

        elif scenario == "timeout_success":
            # Upstream provider actually succeeded, but caller receives timeout
            self._provider_store[provider_ref] = "SUCCEEDED"
            raise ProviderTimeoutException(provider_reference=provider_ref)

        elif scenario == "timeout_fail":
            # Upstream provider failed, caller receives timeout
            self._provider_store[provider_ref] = "FAILED"
            raise ProviderTimeoutException(provider_reference=provider_ref)

        elif scenario == "timeout_unknown":
            # Upstream provider status is unknown, caller receives timeout
            self._provider_store[provider_ref] = "UNKNOWN"
            raise ProviderTimeoutException(provider_reference=provider_ref)

        elif scenario == "slow":
            # Simulates slow network then success
            self._provider_store[provider_ref] = "SUCCEEDED"
            return ProviderChargeResult(outcome="SUCCESS", provider_reference=provider_ref)

        else:
            self._provider_store[provider_ref] = "SUCCEEDED"
            return ProviderChargeResult(outcome="SUCCESS", provider_reference=provider_ref)

    async def query_status(self, provider_reference: str) -> ProviderStatusResult:
        """Query status of a transaction at provider."""
        status = self._provider_store.get(provider_reference, "UNKNOWN")
        return ProviderStatusResult(status=status, provider_reference=provider_reference)

    async def refund(
        self,
        provider_reference: str,
        amount: int,
        currency: str,
        scenario: str = "success",
    ) -> ProviderRefundResult:
        """Simulate refund to upstream provider."""
        refund_ref = f"sim_ref_{uuid.uuid4().hex[:16]}"
        if scenario == "success":
            return ProviderRefundResult(outcome="SUCCESS", provider_reference=refund_ref)
        elif scenario == "decline":
            return ProviderRefundResult(
                outcome="DECLINE",
                provider_reference=refund_ref,
                failure_code="REFUND_DECLINED",
            )
        elif scenario == "timeout":
            raise ProviderTimeoutException(provider_reference=refund_ref)
        return ProviderRefundResult(outcome="SUCCESS", provider_reference=refund_ref)

    def sign_payload(self, timestamp: int, payload_str: str, secret: Optional[str] = None) -> str:
        """HMAC-SHA256 signature of {timestamp}.{payload}."""
        use_secret = secret or self.secret
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        return hmac.new(use_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def verify_signature(
        self,
        timestamp_str: Optional[str],
        signature: Optional[str],
        payload_bytes: bytes,
        now_ts: Optional[int] = None,
    ) -> bool:
        """Verify webhook signature and timestamp tolerance."""
        # Check BUG-006: accepts webhook when missing signature header
        if settings.PL_DEFECT_BUG_006 and not signature:
            return True

        if not signature or not timestamp_str:
            return False

        try:
            ts = int(timestamp_str)
        except ValueError:
            return False

        # Verify timestamp tolerance +- 300s
        current_time = now_ts if now_ts is not None else int(time.time())
        if abs(current_time - ts) > settings.WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            return False

        expected_sig = self.sign_payload(ts, payload_bytes.decode("utf-8"))
        return hmac.compare_digest(expected_sig, signature)


# Global singleton simulator instance
provider_simulator = ProviderSimulator()

