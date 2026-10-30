from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    # Webhook
    WEBHOOK_SECRET: str = "dev-webhook-secret-key-min-32-chars!!"
    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS: int = 300

    # Business timezone & cutoff
    BUSINESS_TIMEZONE: str = "Asia/Ho_Chi_Minh"

    # Payment Rules
    VND_MIN_AMOUNT: int = 1_000
    VND_MAX_AMOUNT: int = 50_000_000
    USD_MIN_AMOUNT: int = 50  # cents ($0.50)
    USD_MAX_AMOUNT: int = 1_000_000  # cents ($10,000)
    PAYMENT_EXPIRY_MINUTES: int = 30
    STATUS_QUERY_MAX_ATTEMPTS: int = 5
    PROVIDER_TIMEOUT_SECONDS: int = 10

    # Idempotency
    IDEMPOTENCY_TTL_HOURS: int = 24

    # Refund
    REFUND_WINDOW_DAYS: int = 180
    MAX_REFUNDS_PER_PAYMENT: int = 10
    REFUND_APPROVAL_THRESHOLD_VND: int = 10_000_000
    REFUND_APPROVAL_THRESHOLD_USD_CENTS: int = 40_000

    # Seeded Defects (feature flags)
    PL_DEFECT_BUG_001: bool = Field(default=False, description="Refund uses < instead of <= (rejects exact refundable)")
    PL_DEFECT_BUG_002: bool = Field(default=False, description="Idempotency ignores payload hash")
    PL_DEFECT_BUG_003: bool = Field(default=False, description="No webhook event_id dedupe")
    PL_DEFECT_BUG_004: bool = Field(default=False, description="Timeout treated as FAILED and retried")
    PL_DEFECT_BUG_005: bool = Field(default=False, description="Refundable ignores PROCESSING/UNKNOWN reservation")
    PL_DEFECT_BUG_006: bool = Field(default=False, description="Accepts webhook without signature header")
    PL_DEFECT_BUG_007: bool = Field(default=False, description="Allows VND 50,000,001")
    PL_DEFECT_BUG_008: bool = Field(default=False, description="No row lock on confirm")
    PL_DEFECT_BUG_009: bool = Field(default=False, description="USD amount compared as float")
    PL_DEFECT_BUG_010: bool = Field(default=False, description="Cutoff uses UTC instead of +07")
    PL_DEFECT_BUG_011: bool = Field(default=False, description="Late webhook overwrites terminal status")
    PL_DEFECT_BUG_012: bool = Field(default=False, description="Refund window rejects day 180")
    PL_DEFECT_BUG_013: bool = Field(default=False, description="Rerun reconciliation duplicates findings")
    PL_DEFECT_BUG_014: bool = Field(default=False, description="UI shows success for UNKNOWN status")
    PL_DEFECT_BUG_015: bool = Field(default=False, description="Logs print authorization header or secrets")
    PL_DEFECT_BUG_016: bool = Field(default=False, description="Wallet check-then-act without lock")
    PL_DEFECT_BUG_017: bool = Field(default=False, description="No ownership check on payment lookup")
    PL_DEFECT_BUG_018: bool = Field(default=False, description="Saves and replays 5xx errors before commit")


settings = Settings()
