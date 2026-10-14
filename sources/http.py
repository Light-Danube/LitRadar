from __future__ import annotations

import math
import time
import urllib.error
import urllib.request

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY = 60.0


def fetch_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
    retries: int = 3,
    backoff: float = 1.0,
) -> bytes:
    """Fetch bytes with conservative retry/backoff for transient failures."""
    attempt = 0
    while True:
        request = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt >= retries:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            delay = _retry_delay(attempt, backoff, retry_after)
            attempt += 1
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt >= retries:
                raise
            delay = _retry_delay(attempt, backoff, None)
            attempt += 1
            time.sleep(delay)


def _retry_delay(attempt: int, backoff: float, retry_after: str | None) -> float:
    """Treat provider delay hints as untrusted; never wait over one minute."""
    if retry_after:
        try:
            requested = float(retry_after)
            if math.isfinite(requested):
                return min(max(requested, 0.0), MAX_RETRY_DELAY)
        except (ValueError, OverflowError):
            pass
    # Invalid/non-finite server hints fall back to the local bounded policy.
    if math.isnan(backoff):
        return 0.0
    try:
        delay = max(backoff, 0.0) * (2**attempt)
    except OverflowError:
        return MAX_RETRY_DELAY if backoff > 0 else 0.0
    return min(delay, MAX_RETRY_DELAY)
