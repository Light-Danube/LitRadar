from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import research_digest
from pipeline import SearchSummary
from sources.base import Paper
from storage.sqlite import PaperStore


def _scan_config(path: Path, *, query_list=None) -> Path:
    payload = {
        "name": "test scan",
        "queries": query_list or [
            {"name": "context", "query": "adaptive context emotion recognition", "sources": ["openalex"], "per_source": 5}
        ],
        "scan": {"semantic": False},
        "digest": {"limit": 10, "queue_limit": 3},
        "overlap": {"candidates": 100, "min_similarity": 0.2, "title_similarity": 0.4},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _add(store: PaperStore, title: str, abstract: str, *, status="new", doi=None) -> int:
    paper = Paper(
        source="fixture",
        title=title,
        abstract=abstract,
        published_at="2026-10-01",
        doi=doi,
        url="https://example.org/paper",
    )
    paper_id = store.upsert_paper(
        paper,
        relevance_score=0.73,
        matched_groups={"adaptive_context": ["adaptive context"]},
        keyword_score=0.73,
        scoring_version="keyword-test",
    )
    if status != "new":
        store.set_status(paper_id, status)
    return paper_id


def test_load_scan_config_validates_sources_and_bounds(tmp_path: Path):
    cfg_path = _scan_config(tmp_path / "digest.json", query_list=[
        {"name": "wide", "query": "adaptive context", "sources": ["openalex"], "per_source": 999}
    ])
    payload = research_digest.load_scan_config(cfg_path)
    assert payload["queries"][0].per_source == 100
    assert payload["semantic"] is False

    bad_path = _scan_config(tmp_path / "bad.json", query_list=[
        {"name": "bad", "query": "adaptive context", "sources": ["unknown-provider"], "per_source": 5}
    ])
    with pytest.raises(ValueError, match="unknown source"):
        research_digest.load_scan_config(bad_path)


def test_scheduled_scan_uses_configured_queries_and_records_history(monkeypatch, tmp_path: Path):
    db = tmp_path / "library.sqlite3"
    cfg = _scan_config(tmp_path / "digest.json", query_list=[
        {"name": "q1", "query": "adaptive context", "sources": ["openalex"], "per_source": 5},
        {"name": "q2", "query": "sarcasm detection", "sources": ["arxiv"], "per_source": 7},
    ])
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"name": "test", "description": "test", "groups": []}), encoding="utf-8")
    calls = []

    def fake_search(query, **kwargs):
        calls.append((query, kwargs["sources"], kwargs["per_source"], kwargs["semantic"]))
        return SearchSummary(query, 3, 0, 0, {kwargs["sources"][0]: 3}, {}, "keyword-v0.1"), []

    monkeypatch.setattr(research_digest, "search_and_ingest", fake_search)
    result = research_digest.run_scheduled_scan(db_path=db, profile_path=profile, config_path=cfg)
    assert result.query_count == 2
    assert result.fetched == 6
    assert calls == [
        ("adaptive context", ("openalex",), 5, False),
        ("sarcasm detection", ("arxiv",), 7, False),
    ]
    store = PaperStore(db)
    try:
        row = store.conn.execute("SELECT job, status, summary_json FROM research_runs WHERE id=?", (result.run_id,)).fetchone()
        assert row["job"] == "scan"
        assert row["status"] == "succeeded"
        assert json.loads(row["summary_json"])["query_count"] == 2
    finally:
        store.close()


def test_digest_includes_new_papers_reading_queue_and_overlap_caveat(tmp_path: Path):
    db = tmp_path / "library.sqlite3"
    cfg = _scan_config(tmp_path / "digest.json")
    store = PaperStore(db)
    try:
        old_id = _add(store, "Adaptive context selection for emotion recognition", "We study adaptive context selection for emotion recognition in conversations.")
        old = store.get(old_id)
        older = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(timespec="seconds")
        store.conn.execute("UPDATE papers SET created_at=? WHERE id=?", (older, old_id))
        store.conn.commit()
        new_id = _add(store, "Adaptive context selection improves emotion recognition", "This paper studies adaptive context selection and emotion recognition in conversational text.")
        queue_id = _add(store, "Survey of contextual emotion models", "A survey of context for emotion recognition.", status="to-read")
        store.conn.execute("UPDATE papers SET created_at=? WHERE id=?", (older, queue_id))
        store.conn.commit()
    finally:
        store.close()

    result = research_digest.build_digest(
        db_path=db,
        period="weekly",
        since=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        limit=10,
        queue_limit=3,
        config_path=cfg,
    )
    assert new_id in result.paper_ids
    assert old_id not in result.paper_ids
    assert "New papers: 1" in result.text
    assert "Reading queue (1 item(s); showing 1)" in result.text
    assert f"#{queue_id}" in result.text
    assert "do not determine whether a dissertation topic is novel" in result.text
    assert result.warnings_count >= 1


def test_overlap_checker_ignores_nonmatching_catalog_papers(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        old_id = _add(store, "Solar cell manufacturing cost estimates", "A study of silicon photovoltaic manufacturing and cost forecasting.")
        new_id = _add(store, "Adaptive context selection for emotion recognition", "Adaptive context selection improves emotion recognition in online conversations.")
        warnings = research_digest.find_overlap_warnings(
            store,
            [store.get(new_id)],
            candidates_limit=100,
            min_similarity=0.9,
            title_similarity=0.9,
        )
        assert not warnings
    finally:
        store.close()


def test_split_telegram_message_respects_length_limit():
    text = "Paragraph one.\n\n" + ("context attribution " * 500) + "\n\nParagraph three."
    chunks = research_digest._split_message(text, 600)
    assert len(chunks) > 1
    assert all(len(chunk) <= 600 for chunk in chunks)
    assert "Paragraph one." in chunks[0]
    assert "Paragraph three." in chunks[-1]


def test_send_telegram_uses_plain_text_api_and_sends_all_chunks(monkeypatch):
    seen = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"ok": true, "result": {"message_id": 7}}'

    def fake_urlopen(request, timeout=0):
        seen.append((request.full_url, json.loads(request.data.decode("utf-8")), timeout))
        return Response()

    monkeypatch.setattr(research_digest.urllib.request, "urlopen", fake_urlopen)
    count = research_digest.send_telegram("hello\n\n" + ("paper " * 700), token="secret-token", chat_id="42")
    assert count == len(seen)
    assert len(seen) >= 2
    assert all("botsecret-token/sendMessage" in url for url, _, _ in seen)
    assert all(payload["chat_id"] == "42" for _, payload, _ in seen)
    assert all(payload["disable_web_page_preview"] is True for _, payload, _ in seen)


def test_cli_exposes_scan_digest_scheduler_and_telegram_tools():
    from cli import build_parser

    parser = build_parser()
    scan = parser.parse_args(["scan", "--no-semantic"])
    assert scan.command == "scan" and scan.semantic is False
    digest = parser.parse_args(["digest", "--period", "daily", "--send"])
    assert digest.command == "digest" and digest.period == "daily" and digest.send is True
    schedule = parser.parse_args(["schedule", "install", "--job", "digest", "--frequency", "weekly", "--time", "09:00"])
    assert schedule.command == "schedule" and schedule.job == "digest" and schedule.frequency == "weekly"
    chats = parser.parse_args(["telegram-chats"])
    assert chats.command == "telegram-chats"


def test_keyword_only_scheduled_refresh_does_not_erase_existing_semantic_score(monkeypatch, tmp_path: Path):
    import pipeline
    from config import RadarConfig

    db = tmp_path / "library.sqlite3"
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "name": "test profile", "description": "adaptive context emotion",
        "groups": [{"name": "context", "weight": 1, "terms": ["adaptive context", "emotion recognition"]}],
    }), encoding="utf-8")
    store = PaperStore(db)
    try:
        existing_id = store.upsert_paper(
            Paper(source="openalex", title="Adaptive context for emotion recognition", abstract="A test abstract", doi="10.1234/existing"),
            relevance_score=0.91, matched_groups={"context": ["adaptive context"]},
            keyword_score=0.6, semantic_score=0.98, scoring_version="semantic-v0.2:test-model",
        )
    finally:
        store.close()

    refreshed = Paper(source="openalex", title="Adaptive context for emotion recognition", abstract="A test abstract", doi="10.1234/existing")
    monkeypatch.setattr(pipeline, "search_all_sources", lambda *args, **kwargs: ({"openalex": [refreshed]}, {}))
    summary, ranked = pipeline.search_and_ingest(
        "adaptive context", db_path=db, profile_path=profile, semantic=False,
        sources=("openalex",), per_source=5, config=RadarConfig(),
    )
    store = PaperStore(db)
    try:
        row = store.get(existing_id)
        assert row["relevance_score"] == pytest.approx(0.91)
        assert row["keyword_score"] == pytest.approx(0.6)
        assert row["semantic_score"] == pytest.approx(0.98)
        assert row["scoring_version"] == "semantic-v0.2:test-model"
    finally:
        store.close()


def test_telegram_digest_backlog_does_not_drop_items_beyond_limit(tmp_path: Path):
    db = tmp_path / "library.sqlite3"
    cfg = _scan_config(tmp_path / "digest.json")
    store = PaperStore(db)
    try:
        ids = [
            _add(store, f"Context selection work {n}", f"Adaptive context selection for emotion recognition paper variant {n}.")
            for n in range(3)
        ]
    finally:
        store.close()

    first = research_digest.build_digest(
        db_path=db, period="weekly", limit=2, queue_limit=0,
        config_path=cfg, channel="telegram",
    )
    assert len(first.paper_ids) == 2
    store = PaperStore(db)
    try:
        sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        store.record_digest_delivery(
            channel="telegram", period="weekly", generated_at=first.generated_at,
            sent_at=sent_at, since_at=first.since, paper_ids=first.paper_ids,
            status="sent",
        )
    finally:
        store.close()

    second = research_digest.build_digest(
        db_path=db, period="weekly", limit=2, queue_limit=0,
        config_path=cfg, channel="telegram",
    )
    assert len(second.paper_ids) == 1
    assert set(second.paper_ids).issubset(set(ids))
    assert set(first.paper_ids).isdisjoint(second.paper_ids)


def test_manual_telegram_digest_loads_dotenv_before_delivery(monkeypatch, tmp_path: Path, capsys):
    import os
    from argparse import Namespace
    import cli
    import config

    db = tmp_path / "library.sqlite3"
    cfg = _scan_config(tmp_path / "digest.json")

    def fake_load():
        os.environ["LITRADAR_TELEGRAM_BOT_TOKEN"] = "test-token-from-dotenv"
        os.environ["LITRADAR_TELEGRAM_CHAT_ID"] = "12345"

    def fake_send(text):
        assert os.environ.get("LITRADAR_TELEGRAM_BOT_TOKEN") == "test-token-from-dotenv"
        assert os.environ.get("LITRADAR_TELEGRAM_CHAT_ID") == "12345"
        return 1

    monkeypatch.delenv("LITRADAR_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("LITRADAR_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(config, "_load_dotenv", fake_load)
    monkeypatch.setattr(cli, "send_telegram", fake_send)
    args = Namespace(
        db=str(db), config=str(cfg), output=None, limit=10, queue_limit=3,
        period="daily", since=None, send=True,
    )
    assert cli.cmd_digest(args) == 0
    assert "Telegram delivery succeeded" in capsys.readouterr().out
    store = PaperStore(db)
    try:
        row = store.conn.execute("SELECT status, sent_at FROM digest_deliveries WHERE channel='telegram'").fetchone()
        assert row["status"] == "sent"
        assert row["sent_at"]
    finally:
        store.close()


def test_telegram_chats_loads_dotenv_before_lookup(monkeypatch, capsys):
    import os
    from argparse import Namespace
    import cli
    import config

    def fake_load():
        os.environ["LITRADAR_TELEGRAM_BOT_TOKEN"] = "test-token-from-dotenv"

    def fake_chats():
        assert os.environ.get("LITRADAR_TELEGRAM_BOT_TOKEN") == "test-token-from-dotenv"
        return [{"chat_id": "12345", "type": "private", "label": "research chat"}]

    monkeypatch.delenv("LITRADAR_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr(config, "_load_dotenv", fake_load)
    monkeypatch.setattr(cli, "telegram_chat_ids", fake_chats)
    assert cli.cmd_telegram_chats(Namespace()) == 0
    output = capsys.readouterr().out
    assert "chat_id=12345" in output
    assert "research chat" in output


def test_digest_can_hide_overlap_section_without_disabling_other_sections(tmp_path: Path):
    db = tmp_path / "library.sqlite3"
    cfg = _scan_config(tmp_path / "digest.json")
    payload = json.loads(cfg.read_text(encoding="utf-8"))
    payload["digest"]["include_overlap"] = False
    cfg.write_text(json.dumps(payload), encoding="utf-8")
    store = PaperStore(db)
    try:
        _add(store, "Adaptive context selection for emotion recognition", "Context selection for conversational emotion recognition.")
    finally:
        store.close()
    result = research_digest.build_digest(db_path=db, period="weekly", config_path=cfg)
    assert "Possible overlap / related works" not in result.text
    assert "Reading queue" in result.text
    assert result.warnings_count == 0
