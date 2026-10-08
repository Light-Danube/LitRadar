from __future__ import annotations

import time
import urllib.error
import urllib.request

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


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
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return max(backoff, 0.0) * (2**attempt)
