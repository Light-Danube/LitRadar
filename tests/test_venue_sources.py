"""Synthetic provider fixtures; these tests never contact scholarly APIs."""
from copy import deepcopy
import json
import urllib.error

import pytest

from sources import openalex, venues


def source(source_id="S1", **fields):
    return {"id": f"https://openalex.org/{source_id}", "display_name": "Same Journal",
            "type": "journal", "issn_l": "1234-5678", "issn": ["1234-5678"],
            "host_organization_name": "Example Publisher", **fields}


def work(**fields):
    return {"id": "https://openalex.org/W1", "display_name": "Emotion context",
            "publication_year": 2024, "publication_date": "2024-01-01",
            "primary_location": {"source": source()}, **fields}


def fake_search(monkeypatch, items=None, count=1):
    calls = []
    def response(url, params, **kwargs):
        calls.append((url, deepcopy(params), kwargs))
        if url.startswith(venues.SOURCES_URL):
            return source()
        return {"results": [work()] if items is None else items, "meta": {"count": count}}
    monkeypatch.setattr(openalex, "_get_json", response)
    return calls


def test_colliding_names_remain_distinct_with_original_metadata(monkeypatch):
    records = [source(), source("S2", issn_l="8765-4321", issn=["8765-4321"])]
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: {"results": records})
    result = venues.lookup_venues("Same Journal")
    assert [item.source_id for item in result] == ["S1", "S2"]
    assert result[0].display_name == result[1].display_name
    assert result[0].issn_l != result[1].issn_l
    assert result[0].lookup_query == "Same Journal"
    assert result[0].retrieved_at.endswith("+00:00")
    assert result[0].record_url == "https://api.openalex.org/sources/S1"
    assert result[0].verification_status == "provider_metadata"
    assert all(item.scopus_status == item.wos_status == item.peer_review_status == "unverified" for item in result)


@pytest.mark.parametrize("provider_type,label", [
    ("journal", "journal"), ("conference", "conference/proceedings"),
    ("repository", "repository/preprint"), ("book series", "book series"),
    ("hosting platform", "hosting platform"), ("platform", "hosting platform"),
    (None, "unknown"), ("other", "unknown"),
])
def test_conservative_source_types_missing_issn(monkeypatch, provider_type, label):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: source(type=provider_type, issn=None, issn_l=None))
    result = venues.get_venue("S1")
    assert result.venue_type == label
    assert result.issns == () and result.issn_l is None


def test_platform_name_alone_does_not_establish_venue_type(monkeypatch):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: source(display_name="ACM Digital Library", type=None))
    assert venues.get_venue("S1").venue_type == "unknown"


def test_structured_source_and_inclusive_year_filter(monkeypatch):
    calls = fake_search(monkeypatch, count=51)
    result = venues.search_venue(" sarcasm ", "https://openalex.org/s1", year_from=2023, year_to=2026,
                                 limit=20, page=2, api_key="synthetic-key", retries=0)
    assert len(calls) == 2
    assert calls[1][0] == openalex.BASE_URL
    assert calls[1][1] == {"search": "sarcasm", "filter": "primary_location.source.id:S1,publication_year:2023-2026",
                            "per-page": 20, "page": 2, "api_key": "synthetic-key"}
    assert result.count == 51 and result.truncated and result.page == 2
    assert result.papers[0].external_id == "https://openalex.org/W1"
    assert "synthetic-key" not in result.provenance["record_url"]
    assert result.to_dict()["venue"]["source_id"] == "S1"
    assert result.provenance["retrieved_at"].endswith("+00:00")


@pytest.mark.parametrize("year_from,year_to,expected", [(2023,None,"2023-9999"), (None,2026,"1-2026"), (None,None,None)])
def test_open_year_bounds(monkeypatch, year_from, year_to, expected):
    calls = fake_search(monkeypatch)
    venues.search_venue("context", "S1", year_from=year_from, year_to=year_to)
    actual = calls[1][1]["filter"]
    assert actual == "primary_location.source.id:S1" + (f",publication_year:{expected}" if expected else "")


def test_empty_results_are_distinct_success(monkeypatch):
    fake_search(monkeypatch, [], count=0)
    result = venues.search_venue("context", "S1")
    assert result.papers == [] and result.count == 0 and result.truncated is False


@pytest.mark.parametrize("kwargs", [
    {"source_id": "Same Journal"}, {"source_id": "https://evil.example/S1"},
    {"source_id": "S1,publication_year:2025"}, {"query": ""}, {"query": "a"*1001},
    {"limit": 101}, {"limit": 0}, {"limit": True}, {"page": 101}, {"page": 0},
    {"year_from": 2026, "year_to": 2023}, {"year_from": True}, {"year_to": "2026"},
])
def test_invalid_requests_do_not_fetch(monkeypatch, kwargs):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: pytest.fail("invalid input fetched"))
    args = {"query": "context", "source_id": "S1", **kwargs}
    with pytest.raises(ValueError):
        venues.search_venue(**args)


@pytest.mark.parametrize("record", [[], {}, source(id="W1"), source(display_name=17),
    source(issn="1234-5678"), source(issn={}), source(issn_l=17), source(type=[]), source(host_organization_name={})])
def test_malformed_source_record_explicit(monkeypatch, record):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: record)
    with pytest.raises(venues.VenueMetadataError):
        venues.get_venue("S1")


def test_get_identity_mismatch_explicit(monkeypatch):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: source("S2"))
    with pytest.raises(venues.VenueMetadataError, match="different source"):
        venues.get_venue("S1")


@pytest.mark.parametrize("item", [work(primary_location={"source": source("S2")}),
    work(publication_year=2022), work(publication_year=None), work(ids=[]),
    work(authorships=[{"author": 4}]), work(abstract_inverted_index={"context": [None, 1]}),
    work(cited_by_count="unknown"), work(publication_date=42), work(id=None),
    work(display_name=None), work(doi={}), "bad"])
def test_malformed_or_contaminated_work_is_not_silently_filtered(monkeypatch, item):
    fake_search(monkeypatch, [item])
    with pytest.raises(venues.VenueMetadataError):
        venues.search_venue("context", "S1", year_from=2023, year_to=2026)


@pytest.mark.parametrize("payload", [{}, {"results": [], "meta": {"count": "0"}},
    {"results": [], "meta": {"count": -1}}, {"results": {}, "meta": {"count": 0}},
    {"results": [work()], "meta": {"count": 0}}])
def test_bad_results_not_reported_as_zero(monkeypatch, payload):
    monkeypatch.setattr(openalex, "_get_json", lambda url, *a, **k: source() if url.startswith(venues.SOURCES_URL) else payload)
    with pytest.raises(venues.VenueMetadataError):
        venues.search_venue("context", "S1")


@pytest.mark.parametrize("error", [urllib.error.HTTPError("https://api.openalex.org", 429, "rate limited", {}, None),
    urllib.error.HTTPError("https://api.openalex.org", 503, "unavailable", {}, None),
    urllib.error.HTTPError("https://api.openalex.org", 403, "denied", {}, None),
    TimeoutError("timed out"), urllib.error.URLError("offline")])
def test_provider_failures_propagate_distinctly(monkeypatch, error):
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(openalex, "_get_json", failed)
    with pytest.raises(type(error)) as raised:
        venues.lookup_venues("context")
    assert raised.value is error


def test_bounded_http_controls(monkeypatch):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: pytest.fail("unbounded retry fetched"))
    with pytest.raises(ValueError, match="HTTP bounds"):
        venues.lookup_venues("context", retries=100)


def test_oversized_provider_page_is_explicit(monkeypatch):
    monkeypatch.setattr(openalex, "_get_json", lambda *a, **k: {"results": [source(), source("S2")]})
    with pytest.raises(venues.VenueMetadataError):
        venues.lookup_venues("context", limit=1)


@pytest.mark.parametrize("status", [429, 503])
def test_lookup_reuses_bounded_http_retries(monkeypatch, status):
    from sources import http
    calls = []
    delays = []
    def failed(request, timeout):
        calls.append((request.full_url, timeout))
        raise urllib.error.HTTPError(request.full_url, status, "synthetic provider error", {}, None)
    monkeypatch.setattr(http.urllib.request, "urlopen", failed)
    monkeypatch.setattr(http.time, "sleep", delays.append)
    with pytest.raises(urllib.error.HTTPError) as error:
        venues.lookup_venues("context & sarcasm", retries=2, backoff=.5, timeout=3)
    assert error.value.code == status
    assert len(calls) == 3 and delays == [.5, 1.0]
    assert calls[0] == ("https://api.openalex.org/sources?search=context+%26+sarcasm&per-page=10", 3)


def test_malformed_json_becomes_explicit_metadata_error(monkeypatch):
    error = json.JSONDecodeError("malformed", "{", 1)
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(openalex, "_get_json", failed)
    with pytest.raises(venues.VenueMetadataError, match="malformed JSON") as raised:
        venues.lookup_venues("context")
    assert raised.value.__cause__ is error
