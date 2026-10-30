import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is offset-aware in UTC (fixes SQLite returning offset-naive datetimes)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    payment_methods = relationship("PaymentMethod", back_populates="merchant", lazy="selectin")
    payments = relationship("Payment", back_populates="merchant", lazy="selectin")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    type = Column(String(50), nullable=False)  # CARD_TOKEN, WALLET
    token = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    merchant = relationship("Merchant", back_populates="payment_methods", lazy="selectin")
    wallet = relationship("Wallet", back_populates="payment_method", uselist=False, lazy="selectin")


class Wallet(Base):
    __tablename__ = "wallets"

    payment_method_id = Column(String(36), ForeignKey("payment_methods.id"), primary_key=True)
    balance = Column(BigInteger, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="VND")
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

    payment_method = relationship("PaymentMethod", back_populates="wallet", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    public_id = Column(String(64), unique=True, nullable=False, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False, index=True)
    merchant_reference = Column(String(64), nullable=False, index=True)
    payment_method_id = Column(String(36), ForeignKey("payment_methods.id"), nullable=True)
    amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(50), nullable=False, default="CREATED", index=True)
    refunded_amount = Column(BigInteger, nullable=False, default=0)
    needs_review = Column(Boolean, nullable=False, default=False)
    provider_reference = Column(String(64), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    succeeded_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

    merchant = relationship("Merchant", back_populates="payments", lazy="selectin")
    attempts = relationship("PaymentAttempt", back_populates="payment", cascade="all, delete-orphan", lazy="selectin")
    status_history = relationship("PaymentStatusHistory", back_populates="payment", cascade="all, delete-orphan", lazy="selectin")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan", lazy="selectin")


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False, index=True)
    attempt_no = Column(Integer, nullable=False)
    outcome = Column(String(50), nullable=False)  # SUCCESS, DECLINE, TIMEOUT
    provider_reference = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    payment = relationship("Payment", back_populates="attempts", lazy="selectin")


class PaymentStatusHistory(Base):
    __tablename__ = "payment_status_history"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    reason = Column(String(255), nullable=True)
    actor = Column(String(100), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    payment = relationship("Payment", back_populates="status_history", lazy="selectin")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    public_id = Column(String(64), unique=True, nullable=False, index=True)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(50), nullable=False, default="REQUESTED", index=True)
    reason = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    provider_reference = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

    payment = relationship("Payment", back_populates="refunds", lazy="selectin")
    status_history = relationship("RefundStatusHistory", back_populates="refund", cascade="all, delete-orphan", lazy="selectin")


class RefundStatusHistory(Base):
    __tablename__ = "refund_status_history"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    refund_id = Column(String(36), ForeignKey("refunds.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    refund = relationship("Refund", back_populates="status_history", lazy="selectin")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("merchant_id", "endpoint", "key", name="uq_idempotency_merchant_endpoint_key"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    merchant_id = Column(String(36), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    key = Column(String(64), nullable=False, index=True)
    request_hash = Column(String(64), nullable=False)
    state = Column(String(50), nullable=False, default="IN_FLIGHT")  # IN_FLIGHT, COMPLETED
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event_id"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    provider = Column(String(50), nullable=False)
    event_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    provider_sequence = Column(BigInteger, nullable=True)
    verification_status = Column(String(50), nullable=False)  # VERIFIED, FAILED
    processing_status = Column(String(50), nullable=False)  # RECEIVED, PROCESSED, IGNORED, STALE, ORPHAN, FAILED
    raw_payload = Column(JSON, nullable=False)
    received_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"
    __table_args__ = (
        UniqueConstraint("provider", "business_date", "run_no", name="uq_reconciliation_run"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    provider = Column(String(50), nullable=False)
    business_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    run_no = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, SUPERSEDED
    file_checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    findings = relationship("ReconciliationFinding", back_populates="run", cascade="all, delete-orphan", lazy="selectin")


class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("reconciliation_runs.id"), nullable=False, index=True)
    provider_reference = Column(String(64), nullable=False)
    match_result = Column(String(50), nullable=False)  # MATCHED, MISMATCHED


class ReconciliationFinding(Base):
    __tablename__ = "reconciliation_findings"
    __table_args__ = (
        UniqueConstraint("run_id", "provider_reference", "mismatch_type", name="uq_finding_run_ref_type"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("reconciliation_runs.id"), nullable=False, index=True)
    provider_reference = Column(String(64), nullable=False)
    mismatch_type = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)  # HIGH, MEDIUM, LOW
    status = Column(String(50), nullable=False, default="OPEN")  # OPEN, INVESTIGATING, RESOLVED, WRITTEN_OFF
    evidence = Column(JSON, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    run = relationship("ReconciliationRun", back_populates="findings", lazy="selectin")


class ReconciliationQuarantine(Base):
    __tablename__ = "reconciliation_quarantine"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("reconciliation_runs.id"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    raw_line = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
