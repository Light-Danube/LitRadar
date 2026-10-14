from __future__ import annotations

import io
import urllib.error

import pytest

from sources.http import _retry_delay, fetch_bytes


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_fetch_bytes_retries_transient_http_error(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(request, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            headers = {"Retry-After": "0"}
            raise urllib.error.HTTPError(request.full_url, 429, "rate", headers, io.BytesIO())
        return _Response(b"ok")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert fetch_bytes("https://example.test", retries=1, backoff=0) == b"ok"
    assert calls["n"] == 2


def test_fetch_bytes_does_not_retry_non_transient_http_error(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(request, timeout):
        calls["n"] += 1
        headers = {}
        raise urllib.error.HTTPError(request.full_url, 404, "missing", headers, io.BytesIO())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(urllib.error.HTTPError):
        fetch_bytes("https://example.test", retries=3, backoff=0)
    assert calls["n"] == 1


@pytest.mark.parametrize("hint,expected", [
    ("999999999999", 60.0), ("NaN", 2.0), ("inf", 2.0), ("-inf", 2.0),
    ("-3", 0.0), ("not-a-number", 2.0), ("1e9999", 2.0), ("0.25", .25),
])
def test_retry_after_untrusted_values_are_bounded(hint, expected):
    assert _retry_delay(1, 1.0, hint) == expected


@pytest.mark.parametrize("attempt,backoff,expected", [
    (10, 1, 60), (10000, 1, 60), (2, float("inf"), 60),
    (2, float("nan"), 0), (2, -1, 0), (10000, 0, 0),
])
def test_exponential_backoff_is_bounded(attempt, backoff, expected):
    assert _retry_delay(attempt, backoff, None) == expected


def test_provider_retry_after_cannot_force_unbounded_sleep(monkeypatch):
    delays = []
    calls = []
    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 429, "rate", {"Retry-After": "999999999999"}, io.BytesIO())
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("sources.http.time.sleep", delays.append)
    with pytest.raises(urllib.error.HTTPError):
        fetch_bytes("https://example.test", retries=2)
    assert len(calls) == 3 and delays == [60.0, 60.0]
