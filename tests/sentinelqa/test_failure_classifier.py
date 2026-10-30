import pytest
from sentinelqa.domain.failure_classifier import classify_failure


def test_ts_083_classify_assertion_failure():
    trace = "AssertionError: expected 'SUCCEEDED' but got 'FAILED' at line 42\nassert 'FAILED' == 'SUCCEEDED'"
    assert classify_failure(trace) == "ASSERTION"


def test_ts_083_classify_timeout():
    trace = "asyncio.exceptions.TimeoutError: Operation timed out after 5000ms"
    assert classify_failure(trace) == "TIMEOUT"


def test_ts_083_classify_application_error():
    trace = "TypeError: 'NoneType' object is not subscriptable\nInternalServerError at /api/v1/payments"
    assert classify_failure(trace) == "APPLICATION_ERROR"


def test_ts_083_classify_environment_error():
    trace = "ConnectionRefusedError: [Errno 111] Connection refused: localhost:5432"
    assert classify_failure(trace) == "ENVIRONMENT"


def test_ts_083_classify_unknown_on_missing_or_ambiguous():
    assert classify_failure(None) == "UNKNOWN"
    assert classify_failure("") == "UNKNOWN"
    assert classify_failure("   \n\t  ") == "UNKNOWN"
    assert classify_failure("Some completely unmapped error message with no stack trace") == "UNKNOWN"

