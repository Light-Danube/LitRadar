from __future__ import annotations

import math
import json
import socket
import ssl
import time
import urllib.error
import urllib.request

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY = 60.0


def format_provider_error(exc: BaseException) -> str:
    """Fixed public diagnostics, independent of untrusted exception text.

    This formatter does not change/consume exceptions or HTTP responses. Callers
    retain the original exception objects and the existing retry policy.
    """
    if isinstance(exc, urllib.error.HTTPError):
        status = exc.code
        if type(status) is not int or not 100 <= status <= 599:
            return "Provider returned an unexpected HTTP status. Review local configuration and provider availability."
        messages = {
            400: "Provider rejected the request (HTTP 400). Review search settings and provider configuration.",
            401: "Provider authentication failed (HTTP 401). Check the API key locally; do not share credentials in diagnostics.",
            403: "Provider access denied (HTTP 403). Check API permissions, network/proxy policy and provider availability.",
            404: "Provider endpoint or record not found (HTTP 404). Review the source identity and installation.",
            429: "Provider rate limited the request (HTTP 429). Wait before retrying or reduce request frequency.",
        }
        if status in messages:
            return messages[status]
        if status >= 500:
            return f"Provider service unavailable (HTTP {status}). Retry later."
        return f"Provider returned an unexpected HTTP status ({status}). Review local configuration and provider availability."
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "Provider request timed out. Check connectivity and retry later."
    if isinstance(reason, socket.gaierror):
        return "Provider name resolution failed. Check DNS/network settings and retry."
    if isinstance(reason, ssl.SSLError):
        return "Provider secure connection failed. Check certificate trust and system time; do not disable TLS verification."
    if isinstance(exc, (urllib.error.URLError, OSError)):
        return "Provider network/proxy connection failed. Check connectivity and proxy settings and retry."
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)):
        return "Provider returned invalid JSON or text. Retry later and check provider availability."
    return "Provider request failed locally. Review configuration and installation before retrying."


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
