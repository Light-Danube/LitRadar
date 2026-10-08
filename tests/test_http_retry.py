from __future__ import annotations

import io
import urllib.error

import pytest

from sources.http import fetch_bytes


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
