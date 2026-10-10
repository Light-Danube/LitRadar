from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from config import RadarConfig
from pipeline import SearchSummary, search_and_ingest
from storage.sqlite import PaperStore

ROOT = Path(__file__).resolve().parent
DEFAULT_SCAN_CONFIG = ROOT / "digest_config.json"
DEFAULT_PROFILE = ROOT / "research_profile.json"
DEFAULT_DB = ROOT / "data" / "litradar.sqlite3"

# Common function words and generic research terms are removed from overlap
# checks so that shared domain vocabulary alone does not trigger a warning.
_STOPWORDS = set("""
a an and are as at be been being by can could did do does for from had has have how
if in into is it its may might more most of on or our paper papers research result
results such than that the their them then there these they this those through to use
used using we what when where which while who will with within without work works
study studies method methods model models approach approaches based analysis using
show shows shown demonstrate demonstrated propose proposed present presented
""".split())
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ScanQuery:
    name: str
    query: str
    sources: tuple[str, ...]
    per_source: int


@dataclass(frozen=True, slots=True)
class ScanResult:
    run_id: int
    query_count: int
    fetched: int
    newly_stored: int
    library_total: int
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DigestResult:
    text: str
    paper_ids: tuple[int, ...]
    since: str
    generated_at: str
    warnings_count: int


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_since(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("--since cannot be empty")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("--since must be an ISO date/time, e.g. 2026-10-01 or 2026-10-01T08:00:00+00:00") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_scan_config(path: str | Path = DEFAULT_SCAN_CONFIG) -> dict[str, Any]:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Scan configuration not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in scan configuration {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Scan configuration must be a JSON object")
    raw_queries = payload.get("queries", [])
    if not isinstance(raw_queries, list):
        raise ValueError("The 'queries' entry must be a list")
    if not raw_queries:
        raise ValueError("No scan queries are configured in digest_config.json")

    default_sources = tuple(RadarConfig.load().enabled_sources)
    default_per_source = _bounded_int(payload.get("per_source", 20), 20, 1, 100)
    parsed: list[ScanQuery] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(raw_queries, start=1):
        if isinstance(item, str):
            name, query, sources, per_source = f"query-{index}", item, default_sources, default_per_source
        elif isinstance(item, dict):
            name = str(item.get("name") or f"query-{index}").strip()
            query = str(item.get("query") or "").strip()
            source_value = item.get("sources", default_sources)
            if isinstance(source_value, str):
                sources = tuple(s.strip().casefold() for s in source_value.split(",") if s.strip())
            elif isinstance(source_value, list):
                sources = tuple(dict.fromkeys(str(s).strip().casefold() for s in source_value if str(s).strip()))
            else:
                raise ValueError(f"Query {name!r}: sources must be a list or comma-separated string")
            per_source = _bounded_int(item.get("per_source", default_per_source), default_per_source, 1, 100)
        else:
            raise ValueError(f"Query {index} must be a string or object")
        if not query:
            continue
        if not sources:
            raise ValueError(f"Query {name!r} has an empty sources list")
        unknown = sorted(set(sources) - {"openalex", "semantic_scholar", "arxiv"})
        if unknown:
            raise ValueError(f"Query {name!r} uses unknown source(s): {', '.join(unknown)}")
        key = (name.casefold(), query.casefold())
        if key in seen:
            continue
        seen.add(key)
        parsed.append(ScanQuery(name=name, query=query, sources=sources, per_source=per_source))
    if not parsed:
        raise ValueError("No valid non-empty queries are configured")

    scan_settings = payload.get("scan", {})
    digest_settings = payload.get("digest", {})
    overlap_settings = payload.get("overlap", {})
    if not isinstance(scan_settings, dict) or not isinstance(digest_settings, dict) or not isinstance(overlap_settings, dict):
        raise ValueError("'scan', 'digest', and 'overlap' settings must be JSON objects")
    return {
        "name": str(payload.get("name") or "LitRadar scheduled scan"),
        "queries": parsed,
        "semantic": bool(scan_settings.get("semantic", False)),
        "digest_limit": _bounded_int(digest_settings.get("limit", 15), 15, 1, 100),
        "queue_limit": _bounded_int(digest_settings.get("queue_limit", 5), 5, 0, 20),
        "overlap_candidates": _bounded_int(overlap_settings.get("candidates", 500), 500, 50, 5000),
        "overlap_min_similarity": _bounded_float(overlap_settings.get("min_similarity", 0.24), 0.24, 0.0, 1.0),
        "overlap_title_similarity": _bounded_float(overlap_settings.get("title_similarity", 0.42), 0.42, 0.0, 1.0),
    }


def _bounded_int(value: Any, default: int, lower: int, upper: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, lower), upper)


def _bounded_float(value: Any, default: float, lower: float, upper: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return min(max(number, lower), upper)


def run_scheduled_scan(
    *,
    db_path: str | Path = DEFAULT_DB,
    profile_path: str | Path = DEFAULT_PROFILE,
    config_path: str | Path = DEFAULT_SCAN_CONFIG,
    semantic: bool | None = None,
    progress: Callable[[str, str], None] | None = None,
) -> ScanResult:
    """Execute all configured topic searches and persist a concise run history.

    Background scans default to keyword scoring to avoid expensive model downloads
    and to make a scheduled task reliable even on a machine without ML extras.
    Set scan.semantic=true in digest_config.json to opt in to semantic scoring.
    """
    payload = load_scan_config(config_path)
    use_semantic = payload["semantic"] if semantic is None else bool(semantic)
    store = PaperStore(db_path)
    started = _iso(_now())
    before = store.total_count()
    store.close()
    query_summaries: list[dict[str, Any]] = []
    errors: list[str] = []
    fetched_total = 0
    for index, query in enumerate(payload["queries"], start=1):
        if progress:
            progress("started", f"[{index}/{len(payload['queries'])}] {query.name}: {query.query}")
        try:
            summary, ranked = search_and_ingest(
                query.query,
                db_path=db_path,
                profile_path=profile_path,
                semantic=use_semantic,
                sources=query.sources,
                per_source=query.per_source,
                config=RadarConfig.load(),
                progress=(lambda event, source, message: progress(event, f"{query.name} / {source}: {message}")) if progress else None,
            )
            fetched_total += summary.fetched
            for source, error in summary.source_errors.items():
                errors.append(f"{query.name} / {source}: {error}")
            query_summaries.append({
                "name": query.name,
                "query": query.query,
                "fetched": summary.fetched,
                "newly_stored": summary.newly_stored,
                "library_total": summary.library_total,
                "source_results": summary.source_results,
                "source_errors": summary.source_errors,
                "scoring_version": summary.scoring_version,
            })
            if progress:
                progress("completed", f"{query.name}: fetched={summary.fetched}; new={summary.newly_stored}; total={summary.library_total}")
        except Exception as exc:
            message = f"{query.name}: {exc}"
            errors.append(message)
            query_summaries.append({"name": query.name, "query": query.query, "error": message})
            if progress:
                progress("error", message)

    store = PaperStore(db_path)
    try:
        after = store.total_count()
        status = "partial" if errors and query_summaries else ("failed" if errors else "succeeded")
        summary_payload = {
            "config": str(config_path),
            "profile": str(profile_path),
            "semantic": use_semantic,
            "query_count": len(payload["queries"]),
            "queries": query_summaries,
            "fetched": fetched_total,
            "newly_stored": max(0, after - before),
            "library_total": after,
            "errors": errors,
        }
        run_id = store.record_research_run(
            job="scan", started_at=started, completed_at=_iso(_now()),
            status=status, summary=summary_payload, error_message="; ".join(errors)[:2000],
        )
        return ScanResult(
            run_id=run_id,
            query_count=len(payload["queries"]),
            fetched=fetched_total,
            newly_stored=max(0, after - before),
            library_total=after,
            errors=tuple(errors),
        )
    finally:
        store.close()


def _tokenize(value: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall((value or "").casefold()) if token not in _STOPWORDS and not token.isdigit()]


def _row_text(row: Any) -> str:
    return f"{row['title'] or ''} {row['title'] or ''} {row['abstract'] or ''}"


def _cosine_tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    if not docs:
        return []
    document_frequency: Counter[str] = Counter()
    term_counts: list[Counter[str]] = []
    for tokens in docs:
        counts = Counter(tokens)
        term_counts.append(counts)
        document_frequency.update(counts.keys())
    total_docs = len(docs)
    idf = {term: math.log(1.0 + total_docs / (1.0 + df)) + 1.0 for term, df in document_frequency.items()}
    vectors: list[dict[str, float]] = []
    norms: list[float] = []
    for counts in term_counts:
        vector = {term: (1.0 + math.log(count)) * idf[term] for term, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in vector.values()))
        vectors.append(vector)
        norms.append(norm)
    return [{"__norm__": norm, **vector} for vector, norm in zip(vectors, norms)]


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    left_norm = left.get("__norm__", 0.0)
    right_norm = right.get("__norm__", 0.0)
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    # Iterate over the smaller vector for speed and avoid a third-party library.
    if len(left) > len(right):
        left, right = right, left
    dot = sum(value * right.get(term, 0.0) for term, value in left.items() if term != "__norm__")
    return dot / (left_norm * right_norm)


def _title_jaccard(left: str, right: str) -> float:
    a, b = set(_tokenize(left)), set(_tokenize(right))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _assessment_warning(row: Any) -> str | None:
    raw = row["llm_assessment_json"]
    if not raw:
        return None
    try:
        assessment = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    try:
        overlap = float(assessment.get("potential_overlap", 0.0))
    except (TypeError, ValueError):
        overlap = 0.0
    level = str(assessment.get("overlap_level", "low")).casefold()
    if level == "high" or overlap >= 0.70:
        reason = str(assessment.get("overlap_reason") or assessment.get("summary") or "Model flagged possible overlap").strip()
        provider = str(assessment.get("provider") or "LLM")
        return f"LLM triage ({provider}, overlap={overlap:.2f}): {reason}"
    return None


def find_overlap_warnings(
    store: PaperStore,
    new_rows: list[Any],
    *,
    candidates_limit: int = 500,
    min_similarity: float = 0.24,
    title_similarity: float = 0.42,
    max_warnings: int = 12,
) -> list[dict[str, Any]]:
    """Return cautious, explainable overlap signals; these are not novelty claims."""
    if not new_rows:
        return []
    all_rows = store.list_papers(limit=max(candidates_limit, len(new_rows)), sort="relevance_score")
    new_ids = {int(row["id"]) for row in new_rows}
    older = [row for row in all_rows if int(row["id"]) not in new_ids and row["status"] not in {"dismissed", "archived"}]
    # LLM assessment flags can be emitted even if the local library has no
    # older comparison candidates yet.
    warnings: list[dict[str, Any]] = []
    for row in new_rows:
        assessment = _assessment_warning(row)
        if assessment:
            warnings.append({"paper": row, "kind": "model", "message": assessment, "similarity": None, "other": None})
    if not older:
        return warnings[:max_warnings]

    combined = list(new_rows) + older
    token_docs = [_tokenize(_row_text(row)) for row in combined]
    vectors = _cosine_tfidf(token_docs)
    offset = len(new_rows)
    for idx, row in enumerate(new_rows):
        paper_id = int(row["id"])
        matches: list[tuple[float, float, Any, int]] = []
        for old_index, other in enumerate(older, start=offset):
            cosine = _cosine(vectors[idx], vectors[old_index])
            title_sim = _title_jaccard(str(row["title"]), str(other["title"]))
            if cosine >= min_similarity or title_sim >= title_similarity:
                matches.append((max(cosine, title_sim), cosine, other, title_sim))
        matches.sort(key=lambda item: item[0], reverse=True)
        for overall, cosine, other, title_sim in matches[:2]:
            warnings.append({
                "paper": row,
                "kind": "catalog-similarity",
                "similarity": cosine,
                "title_similarity": title_sim,
                "other": other,
                "message": f"Similar to library item #{int(other['id'])} (text similarity {cosine:.2f}, title overlap {title_sim:.2f}). Check whether this is a near-duplicate, adjacent work, or related method.",
            })
            if len(warnings) >= max_warnings:
                return warnings[:max_warnings]
    return warnings[:max_warnings]


def _last_sent_at(store: PaperStore, channel: str) -> datetime | None:
    raw = store.latest_digest_sent_at(channel)
    if not raw:
        return None
    try:
        return _parse_since(raw)
    except ValueError:
        return None


def _truncate(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build_digest(
    *,
    db_path: str | Path = DEFAULT_DB,
    period: str = "weekly",
    since: str | None = None,
    limit: int = 15,
    queue_limit: int = 5,
    config_path: str | Path = DEFAULT_SCAN_CONFIG,
    channel: str = "preview",
) -> DigestResult:
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be daily or weekly")
    generated_at = _now()
    store = PaperStore(db_path)
    try:
        already_delivered = channel == "telegram" and _last_sent_at(store, channel) is not None
        if since:
            since_dt = _parse_since(since)
        elif already_delivered:
            # Keep a stable baseline and exclude previously delivered paper IDs.
            # This prevents papers beyond a digest's display limit from being
            # skipped forever when the next delivery advances the clock.
            baseline = store.first_digest_since_at(channel) or store.latest_digest_sent_at(channel)
            since_dt = _parse_since(baseline) if baseline else generated_at - timedelta(days=1 if period == "daily" else 7)
        else:
            since_dt = generated_at - timedelta(days=1 if period == "daily" else 7)
        since_iso = _iso(since_dt)
        sent_filter = ""
        params: list[Any] = [since_iso, _iso(generated_at)]
        if already_delivered:
            sent_filter = " AND NOT EXISTS (SELECT 1 FROM digest_delivery_papers dp JOIN digest_deliveries dd ON dd.id=dp.delivery_id WHERE dp.paper_id=papers.id AND dd.channel=? AND dd.status='sent')"
            params.append(channel)
        params.append(max(1, int(limit)))
        order_by = "created_at ASC, relevance_score DESC, citation_count DESC" if already_delivered else "relevance_score DESC, citation_count DESC, published_at DESC, id DESC"
        new_rows = list(store.conn.execute(
            """SELECT * FROM papers AS papers
               WHERE created_at >= ? AND created_at <= ?
                 AND status NOT IN ('dismissed', 'archived')""" + sent_filter + f" ORDER BY {order_by} LIMIT ?",
            params,
        ))
        new_ids = tuple(int(row["id"]) for row in new_rows)
        count_params: list[Any] = [since_iso, _iso(generated_at)]
        if already_delivered:
            count_params.append(channel)
        total_new = int(store.conn.execute(
            """SELECT COUNT(*) AS n FROM papers AS papers
               WHERE created_at >= ? AND created_at <= ?
                 AND status NOT IN ('dismissed', 'archived')""" + sent_filter,
            count_params,
        ).fetchone()["n"])
        queue_count = store.total_count(status="to-read")
        queue_rows = store.list_papers(limit=max(0, int(queue_limit)), status="to-read", sort="relevance_score") if queue_limit else []
        payload = load_scan_config(config_path)
        overlap_warnings = find_overlap_warnings(
            store,
            list(new_rows),
            candidates_limit=payload["overlap_candidates"],
            min_similarity=payload["overlap_min_similarity"],
            title_similarity=payload["overlap_title_similarity"],
        )

        lines = [
            f"LitRadar {period.capitalize()} Research Digest",
            f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Period start: {since_dt.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"New papers: {total_new} (showing {len(new_rows)})",
            "",
        ]
        if not new_rows:
            lines.append("No new papers were added during this period. The scan may have found only works already in the library.")
            lines.append("")
        else:
            for index, row in enumerate(new_rows, start=1):
                authors = []
                try:
                    authors = json.loads(row["authors_json"] or "[]")
                except json.JSONDecodeError:
                    pass
                author_text = ", ".join(str(a) for a in authors[:3])
                if len(authors) > 3:
                    author_text += " et al."
                published = row["published_at"] or "date n/a"
                lines.append(f"{index}. **{_truncate(row['title'], 180)}**")
                lines.append(f"   - Library ID: {int(row['id'])} | score: {float(row['relevance_score']):.3f} | {published} | citations: {int(row['citation_count'] or 0)}")
                if author_text:
                    lines.append(f"   - Authors: {_truncate(author_text, 160)}")
                if row["venue"]:
                    lines.append(f"   - Venue: {_truncate(row['venue'], 120)}")
                if row["doi"]:
                    doi = str(row["doi"]).strip()
                    doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                    lines.append(f"   - DOI: {doi_url}")
                elif row["url"]:
                    lines.append(f"   - URL: {row['url']}")
                try:
                    groups = json.loads(row["matched_groups_json"] or "{}")
                except json.JSONDecodeError:
                    groups = {}
                group_names = list(groups) if isinstance(groups, dict) else []
                if group_names:
                    lines.append(f"   - Profile signals: {', '.join(group_names[:5])}")
                if row["abstract"]:
                    lines.append(f"   - Abstract: {_truncate(row['abstract'], 340)}")
                lines.append("")

        lines.extend(["## Possible overlap / related works", ""])
        if not overlap_warnings:
            lines.append("No strong overlap signals were detected by the configured checks. This does not establish novelty.")
        else:
            for warning in overlap_warnings:
                paper = warning["paper"]
                if warning["kind"] == "model":
                    lines.append(f"- **{_truncate(paper['title'], 120)}** — {warning['message']}")
                else:
                    other = warning["other"]
                    lines.append(
                        f"- **{_truncate(paper['title'], 120)}** — {warning['message']} "
                        f"Existing work: **{_truncate(other['title'], 140)}**."
                    )
        lines.extend([
            "",
            "*Overlap signals are heuristic/advisory. They can surface related methods or shared vocabulary; they do not determine whether a dissertation topic is novel.*",
            "",
            f"## Reading queue ({queue_count} item(s); showing {len(queue_rows)})",
            "",
        ])
        if not queue_rows:
            lines.append("The reading queue is empty.")
        else:
            for row in queue_rows:
                lines.append(f"- #{int(row['id'])} **{_truncate(row['title'], 150)}** — score {float(row['relevance_score']):.3f}; added {str(row['created_at'])[:10]}")
        lines.extend(["", "---", "Generated locally by LitRadar. Do not treat ranking scores or overlap alerts as a substitute for reading the paper.", ""])
        return DigestResult(text="\n".join(lines), paper_ids=new_ids, since=since_iso, generated_at=_iso(generated_at), warnings_count=len(overlap_warnings))
    finally:
        store.close()


def send_telegram(text: str, *, token: str | None = None, chat_id: str | None = None) -> int:
    """Send a plain-text digest via Telegram Bot API without logging credentials."""
    token = token or os.getenv("LITRADAR_TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("LITRADAR_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("Telegram delivery requires LITRADAR_TELEGRAM_BOT_TOKEN and LITRADAR_TELEGRAM_CHAT_ID in .env")
    # Telegram sends plain text below, so strip Markdown emphasis/heading markers
    # rather than exposing literal **bold** and ## heading syntax to the reader.
    telegram_text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    telegram_text = re.sub(r"\*\*(.*?)\*\*", r"\1", telegram_text)
    telegram_text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", telegram_text)
    chunks = _split_message(telegram_text, 3500)
    sent = 0
    for chunk in chunks:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        attempts = 0
        while True:
            attempts += 1
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not payload.get("ok"):
                    description = str(payload.get("description") or "Telegram API rejected the message")
                    raise RuntimeError(f"Telegram API error: {description[:300]}")
                sent += 1
                break
            except urllib.error.HTTPError as exc:
                # API URL contains the secret token; never include the exception's URL in errors.
                body_text = ""
                try:
                    body_text = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                if exc.code == 429 and attempts < 3:
                    try:
                        retry_after = int(json.loads(body_text).get("parameters", {}).get("retry_after", 2))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        retry_after = 2
                    time.sleep(min(max(retry_after, 1), 10))
                    continue
                detail = ""
                try:
                    detail = str(json.loads(body_text).get("description") or "")
                except (ValueError, json.JSONDecodeError):
                    pass
                raise RuntimeError(f"Telegram HTTP {exc.code}" + (f": {detail[:250]}" if detail else "")) from None
            except urllib.error.URLError as exc:
                raise RuntimeError(f"Telegram connection failed: {getattr(exc, 'reason', 'network error')}") from None
    return sent


def _split_message(text: str, max_chars: int) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            # Long abstracts are split into bounded chunks without truncating content.
            pieces = [paragraph[index:index + max_chars] for index in range(0, len(paragraph), max_chars)]
        else:
            pieces = [paragraph]
        for piece in pieces:
            proposed = piece if not current else f"{current}\n\n{piece}"
            if len(proposed) > max_chars and current:
                chunks.append(current)
                current = piece
            else:
                current = proposed
    if current:
        chunks.append(current)
    return chunks or ["LitRadar digest: no content."]


def telegram_chat_ids(token: str | None = None) -> list[dict[str, str]]:
    """List chat identifiers of recent updates, never message contents."""
    token = token or os.getenv("LITRADAR_TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Set LITRADAR_TELEGRAM_BOT_TOKEN in .env first")
    url = f"https://api.telegram.org/bot{token}/getUpdates?allowed_updates=%5B%22message%22%2C%22channel_post%22%5D&limit=100"
    request = urllib.request.Request(url, headers={"User-Agent": "LitRadar/0.7.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram getUpdates returned HTTP {exc.code}; check the bot token") from None
    except urllib.error.URLError:
        raise RuntimeError("Telegram getUpdates network request failed") from None
    if not payload.get("ok"):
        raise RuntimeError("Telegram getUpdates failed; check the bot token")
    found: dict[str, dict[str, str]] = {}
    for update in payload.get("result", []):
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        if "id" not in chat:
            continue
        chat_id = str(chat["id"])
        title = str(chat.get("title") or chat.get("username") or chat.get("first_name") or chat.get("type") or "chat")
        found[chat_id] = {"chat_id": chat_id, "type": str(chat.get("type") or "unknown"), "label": title}
    return list(found.values())
