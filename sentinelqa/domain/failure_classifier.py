from typing import Optional


def classify_failure(error_trace: Optional[str]) -> str:
    """
    FR-FLK-001 / BR-QE-004 / TS-083:
    Classify failure cause. Default to UNKNOWN if evidence is lacking.
    Categories: ASSERTION, TIMEOUT, APPLICATION_ERROR, ENVIRONMENT, TEST_DEFECT, UNKNOWN
    """
    if not error_trace or not error_trace.strip():
        return "UNKNOWN"

    text = error_trace.lower()

    if "assertionerror" in text or "assert " in text:
        return "ASSERTION"

    if "timeouterror" in text or "timed out" in text or "deadline exceeded" in text:
        return "TIMEOUT"

    if "internalservererror" in text or "500 internal" in text or "nullpointer" in text or "typeerror" in text:
        return "APPLICATION_ERROR"

    if "connection refused" in text or "econnrefused" in text or "port already in use" in text:
        return "ENVIRONMENT"

    return "UNKNOWN"

