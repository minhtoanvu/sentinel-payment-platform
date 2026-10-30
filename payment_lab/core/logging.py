import logging
import re
import structlog
from typing import Any
from payment_lab.core.config import settings


def sanitize_sensitive_data(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Sanitize sensitive headers and secret tokens from logs unless BUG-015 is enabled."""
    if settings.PL_DEFECT_BUG_015:
        # BUG-015: Logs leak Authorization header and secret
        return event_dict

    sanitized = {}
    sensitive_keys = {"authorization", "x-provider-signature", "secret", "token", "password", "card_number"}

    for k, v in event_dict.items():
        key_lower = k.lower()
        if any(s in key_lower for s in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, str):
            # Check for Bearer token patterns
            val = re.sub(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer [REDACTED]", v)
            sanitized[k] = val
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        else:
            sanitized[k] = v
    return sanitized


def sanitize_dict(d: dict[str, Any]) -> dict[str, Any]:
    sensitive_keys = {"authorization", "x-provider-signature", "secret", "token", "password", "card_number"}
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in sensitive_keys):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = sanitize_dict(v)
        else:
            out[k] = v
    return out


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            sanitize_sensitive_data,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()

