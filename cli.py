from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import subprocess
import textwrap
import webbrowser
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.personalization import PersonalizationModel, build_model, explain_candidate, neutral_results, score_rows
from ranking.scoring import Score, rank_papers, score_papers_semantic
from bibliography import export_rows
from offline import DEFAULT_OFFLINE_DIR, is_available_offline, offline_pdf_path, save_paper_offline
from sources.base import Paper
from pipeline import search_and_ingest
from citation_intelligence import explore_citation_graph
from notes import edit_note, export_notes_markdown
from research_digest import (
    DEFAULT_SCAN_CONFIG, build_digest, run_scheduled_scan, send_telegram, telegram_chat_ids,
)
from telegram_bot import LitRadarTelegramBot, TelegramAPIError, configure_listener_logging
from storage.sqlite import PaperStore, SORT_CHOICES, STATUSES

from litradar_runtime import (WORKSPACE_ROOT, CODE_ROOT, SOURCE_CHECKOUT, DEFAULT_DB, DEFAULT_PROFILE, VERSION, ensure_user_defaults)

ROOT = WORKSPACE_ROOT


def _load_profile(path: str | None) -> KeywordProfile:
    return KeywordProfile.from_json(path or DEFAULT_PROFILE)


def _make_embedder(profile: KeywordProfile):
    from ranking.embeddings import SentenceTransformerEmbedder
    return SentenceTransformerEmbedder(profile.embedding_model)


def _rank(papers: list[Paper], profile: KeywordProfile, *, semantic: bool):
    if not semantic:
        return rank_papers(papers, profile)
    try:
        embedder = _make_embedder(profile)
        return score_papers_semantic(papers, profile, embedder)
    except Exception as exc:
        print(f"semantic scoring unavailable: {exc}", file=sys.stderr)
        print("falling back to keyword scoring", file=sys.stderr)
        return rank_papers(papers, profile)


def cmd_init(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    stats = store.stats()
    store.close()
    print(f"Initialized database: {args.db}")
    print(f"Papers stored: {stats['all']}")
    return 0


def cmd_library_backup(args: argparse.Namespace) -> int:
    from storage.recovery import backup_library
    try:
        bundle = backup_library(args.db, args.destination, research=args.research_dir,
                                offline=args.offline_dir, writers_stopped=args.writers_stopped)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"Library backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"Library backup created: {bundle}")
    print("Excluded: credentials, logs, caches, models, profiles/config and scheduler registrations.")
    return 0


def cmd_library_restore(args: argparse.Namespace) -> int:
    from storage.recovery import restore_library
    try:
        database = restore_library(args.bundle, args.destination)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"Library restore failed: {exc}", file=sys.stderr)
        return 1
    print(f"Library restored into new destination: {database}")
    print("Select this database explicitly with --db. Review profile/config and scheduler settings manually.")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    config = RadarConfig.load()
    query = args.query or "adaptive context emotion sarcasm online conversation"
    requested_sources = tuple(args.sources) if args.sources else config.enabled_sources
    print(
        f"Searching {len(requested_sources)} source(s) for: {query!r} "
        f"(up to {args.per_source} papers per source)",
        file=sys.stderr,
        flush=True,
    )

    def report(event: str, source: str, message: str) -> None:
        prefix = {
            "started": "START",
            "cache-hit": "CACHE",
            "completed": "DONE",
            "error": "ERROR",
        }.get(event, event.upper())
        print(f"[{prefix}] {source}: {message}", file=sys.stderr, flush=True)

    summary, ranked = search_and_ingest(
        query,
        db_path=args.db,
        profile_path=args.profile,
        semantic=args.semantic,
        sources=requested_sources,
        per_source=args.per_source,
        config=config,
        progress=report,
    )
    print(
        "Search complete: "
        f"{summary.fetched} result(s) fetched; {summary.newly_stored} new unique paper(s); "
        f"library now contains {summary.library_total} paper(s)."
    )
    print(f"Scoring: {summary.scoring_version}")
    for index, (paper, score) in enumerate(ranked[: args.limit], start=1):
        _print_scored(index, paper, score)
    if not ranked and summary.source_errors:
        return 1
    return 0 if ranked else 1


def _print_scored(index: int, paper: Paper, score: Score) -> None:
    semantic = "n/a" if score.semantic_score is None else f"{score.semantic_score:.3f}"
    print(f"{index:>2}. [{score.total:>5.3f}] {paper.title}")
    print(
        f"    {paper.source} | {paper.published_at or 'date n/a'} "
        f"| keyword={score.keyword_score:.3f} | semantic={semantic} | citations={paper.citation_count}"
    )
    hits = ", ".join(score.group_hits)
    if hits:
        print(f"    matched: {hits}")
    if paper.url:
        print(f"    {paper.url}")


def _format_llm(row) -> str:
    if not row["llm_assessment_json"]:
        return ""
    try:
        llm = json.loads(row["llm_assessment_json"])
    except json.JSONDecodeError:
        return ""
    return f" | LLM relevance={llm.get('relevance', 0):.2f} overlap={llm.get('overlap_level', 'n/a')}"


def _print_rows(rows, score_overrides: dict[int, float] | None = None, reasons: dict[int, str] | None = None) -> None:
    if not rows:
        print("No papers matched the current view.")
        return
    score_overrides = score_overrides or {}
    reasons = reasons or {}
    for index, row in enumerate(rows, start=1):
        semantic = "n/a" if row["semantic_score"] is None else f"{row['semantic_score']:.3f}"
        tags = json.loads(row["tags_json"] or "[]")
        tag_text = f" | tags={','.join(tags)}" if tags else ""
        offline_marker = " | offline" if is_available_offline(row) else ""
        display_score = score_overrides.get(int(row["id"]), float(row["relevance_score"]))
        print(f"{index:>2}. [{display_score:>5.3f}] {row['title']}{offline_marker}")
        print(
            f"    id={row['id']} | {row['status']} | {row['source']} | {row['published_at'] or 'date n/a'} "
            f"| keyword={row['keyword_score']:.3f} | semantic={semantic} | citations={row['citation_count']}"
            f"{tag_text}{_format_llm(row)}"
        )
        if int(row["id"]) in reasons:
            print(f"    Recommended because: {reasons[int(row['id'])]}")
        print(f"    references={row['reference_count'] if row['reference_count'] is not None else 'n/a'} | influential citations={row['influential_citation_count'] if row['influential_citation_count'] is not None else 'n/a'}")
        if row["url"]:
            print(f"    {row['url']}")


def _personalized_view(store: PaperStore, *, profile: KeywordProfile, config: RadarConfig, limit: int, status: str = "all", query: str | None = None, tag: str | None = None, min_score: float | None = None):
    base_rows = store.list_papers(
        limit=config.personalization_scan_limit,
        status=status,
        query=query,
        tag=tag,
        min_score=min_score,
        sort="relevance_score",
    )
    if not config.personalization_enabled:
        return neutral_results(base_rows)[:limit], PersonalizationModel(interactions=0, group_signal={})
    model = build_model(store.feedback_rows(), min_feedback=config.personalization_min_feedback)
    ranked = score_rows(base_rows, model, profile, weight=config.personalized_weight)
    return ranked[:limit], model


def cmd_list(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        total = store.total_count(status=args.status, query=args.query, tag=args.tag, min_score=args.min_score)
        profile = _load_profile(args.profile) if args.sort == "personalized" else None
        if args.sort == "personalized":
            config = RadarConfig.load()
            ranked, model = _personalized_view(
                store,
                profile=profile,
                config=config,
                limit=args.limit,
                status=args.status,
                query=args.query,
                tag=args.tag,
                min_score=args.min_score,
            )
            rows = [row for row, _ in ranked]
            score_overrides = {int(row["id"]): result.score for row, result in ranked}
            personalized_reasons = {
                int(row["id"]): explain_candidate(row, model, profile, weight=config.personalized_weight)
                for row, _result in ranked
            }
            if not config.personalization_enabled:
                print("Personalized ranking is disabled by configuration; showing base relevance.")
            elif model.ready:
                print(f"Personalized ranking active ({model.interactions} feedback actions).")
            else:
                print(f"Personalized ranking needs {config.personalization_min_feedback} feedback actions; showing base relevance.")
        else:
            rows = store.list_papers(
                limit=args.limit,
                status=args.status,
                query=args.query,
                tag=args.tag,
                min_score=args.min_score,
                sort=args.sort,
            )
        if rows:
            print(f"Showing {len(rows)} of {total} stored matching paper(s).")
        else:
            print(f"No papers matched the current view (0 of {total}).")
        _print_rows(
            rows,
            score_overrides if args.sort == "personalized" else None,
            personalized_reasons if args.sort == "personalized" else None,
        )
        return 0
    finally:
        store.close()


def cmd_top(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        if args.sort == "personalized":
            config = RadarConfig.load()
            profile = _load_profile(args.profile)
            ranked, _model = _personalized_view(store, profile=profile, config=config, limit=args.limit)
            _print_rows([row for row, _ in ranked], {int(row["id"]): result.score for row, result in ranked})
        else:
            _print_rows(store.top(args.limit, sort=args.sort))
        return 0
    finally:
        store.close()


def cmd_recent(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    _print_rows(store.recent(args.limit))
    store.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    stats = store.stats()
    store.close()
    for status in ["all", *STATUSES]:
        print(f"{status:>10}: {stats[status]}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    row = store.get(args.paper_id)
    store.close()
    if row is None:
        print("Paper not found.", file=sys.stderr)
        return 1
    print(f"ID: {row['id']}")
    print(f"Title: {row['title']}")
    print(f"Status: {row['status']}")
    print(f"Source: {row['source']}")
    print(f"Published: {row['published_at'] or 'n/a'}")
    print(f"Authors: {', '.join(json.loads(row['authors_json'] or '[]'))}")
    print(f"Venue: {row['venue'] or 'n/a'}")
    print(f"DOI: {row['doi'] or 'n/a'}")
    print(f"URL: {row['url'] or 'n/a'}")
    print(f"Offline PDF: {offline_pdf_path(row) if is_available_offline(row) else 'not saved'}")
    print(f"Citations: {row['citation_count']}")
    print(f"References: {row['reference_count'] if row['reference_count'] is not None else 'n/a'}")
    print(f"Influential citations: {row['influential_citation_count'] if row['influential_citation_count'] is not None else 'n/a'}")
    print(f"Relevance score: {row['relevance_score']:.3f}")
    print(f"Keyword score: {row['keyword_score']:.3f}")
    semantic = row["semantic_score"]
    print(f"Semantic score: {'n/a' if semantic is None else f'{semantic:.3f}'}")
    print(f"Scoring version: {row['scoring_version']}")
    user_tags = json.loads(row["tags_json"] or "[]")
    source_tags = json.loads(row["source_tags_json"] or "[]")
    print(f"Tags: {', '.join(user_tags) or 'none'}")
    print(f"Source tags: {', '.join(source_tags) or 'none'}")
    if row["dismiss_reason"]:
        print(f"Dismiss reason: {row['dismiss_reason']}")
    if row["notes"]:
        print("\nNotes:\n")
        print(row["notes"])
    if row["llm_assessment_json"]:
        print("\nLLM assessment (experimental/advisory):\n")
        print(json.dumps(json.loads(row["llm_assessment_json"]), ensure_ascii=False, indent=2))
    print("\nAbstract:\n")
    print(row["abstract"] or "(no abstract)")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        store.set_status(args.paper_id, args.status)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        store.close()
        return 1
    finally:
        store.close()
    print(f"Paper {args.paper_id} → {args.status}")
    return 0


def cmd_dismiss(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        store.set_status(args.paper_id, "dismissed", dismiss_reason=args.reason)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        store.close()
        return 1
    finally:
        store.close()
    print(f"Dismissed paper {args.paper_id}" + (f" ({args.reason})" if args.reason else "") + ".")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        store.set_status(args.paper_id, args.status)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        store.close()
        return 1
    finally:
        store.close()
    print(f"Restored paper {args.paper_id} → {args.status}")
    return 0


def cmd_tags(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        if args.set_tags is not None:
            tags = [part.strip() for part in args.set_tags.split(",") if part.strip()]
            store.set_tags(args.paper_id, tags)
            print(f"Set tags for paper {args.paper_id}: {', '.join(tags) or 'none'}")
            return 0
        if args.remove:
            store.remove_tags(args.paper_id, args.remove)
            print(f"Removed tags from paper {args.paper_id}.")
            return 0
        if args.tags:
            store.add_tags(args.paper_id, args.tags)
            print(f"Updated tags for paper {args.paper_id}.")
            return 0
        print("No tag changes requested. Use positional tags, --remove, or --set.", file=sys.stderr)
        return 2
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_feedback(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        signal = 1.0 if args.signal == "positive" else -1.0
        store.record_feedback(args.paper_id, signal, reason=args.reason)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(f"Recorded {args.signal} feedback for paper {args.paper_id}.")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        row = store.get(args.paper_id)
        if row is None:
            print(f"Paper not found: {args.paper_id}", file=sys.stderr)
            return 1
        if args.edit:
            try:
                text = edit_note(row["notes"] or "")
            except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
                print(f"Cannot open note editor: {exc}", file=sys.stderr)
                print("Set EDITOR/VISUAL (e.g. code --wait, notepad) or pass note text directly.", file=sys.stderr)
                return 2
        elif args.text is not None:
            text = args.text
        else:
            print("Provide note text or use --edit to open the structured Markdown template.", file=sys.stderr)
            return 2
        store.set_notes(args.paper_id, text)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(f"Updated notes for paper {args.paper_id}.")
    return 0



def cmd_export_bibtex(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        if args.paper_ids:
            rows = []
            for paper_id in args.paper_ids:
                row = store.get(paper_id)
                if row is None:
                    print(f"Paper not found: {paper_id}", file=sys.stderr)
                    return 1
                rows.append(row)
        else:
            rows = store.list_papers(limit=100000, status=args.status, sort="relevance_score")
        count = export_rows(rows, args.output)
    finally:
        store.close()
    print(f"Exported {count} BibTeX entr{'y' if count == 1 else 'ies'} to {args.output}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    if args.paper_ids:
        rows = []
        for paper_id in args.paper_ids:
            row = store.get(paper_id)
            if row is None:
                print(f"Paper not found: {paper_id}", file=sys.stderr)
                store.close()
                return 1
            rows.append(row)
    else:
        rows = store.list_papers(limit=args.limit, status=args.status, sort="relevance_score")

    saved = 0
    pdfs = 0
    unpaywall_email = RadarConfig.load().unpaywall_email
    if unpaywall_email:
        print("Unpaywall OA fallback enabled (direct provider PDF links are tried first).")
    else:
        print("Unpaywall OA fallback disabled; set UNPAYWALL_EMAIL to enable legal DOI-based OA lookup.")
    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] Saving offline bundle: {row['title']}", flush=True)
        result = save_paper_offline(row, args.output_dir, unpaywall_email=unpaywall_email)
        saved += 1
        if result["has_pdf"]:
            pdfs += 1
            detail = f"PDF saved ({result['bytes']} bytes)" if result["downloaded"] else "PDF already present"
        else:
            detail = "metadata + abstract saved; no PDF available"
        print(f"id={row['id']} | {detail} | {result['directory']}")
    store.close()
    print(f"Offline save complete: {saved} paper(s), {pdfs} with PDF.")
    return 0

def cmd_export_notes(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    try:
        rows = store.list_papers(limit=1000000, status=args.status, sort="recent")
        count = export_notes_markdown(rows, args.output)
    finally:
        store.close()
    print(f"Exported notes for {count} paper(s) to {args.output}")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    row = store.get(args.paper_id)
    store.close()
    if row is None:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        return 1
    local_pdf = offline_pdf_path(row)
    if local_pdf.exists():
        webbrowser.open(local_pdf.as_uri())
        print(f"Opened offline PDF: {local_pdf}")
        return 0
    url = row["pdf_url"] or row["url"]
    if not url and row["doi"]:
        doi = str(row["doi"]).strip()
        url = doi if doi.startswith(("https://", "http://")) else f"https://doi.org/{doi}"
    if not url:
        print("Paper has no URL, PDF URL, or DOI.", file=sys.stderr)
        return 1
    webbrowser.open(url)
    print(f"Opened online: {url}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    store = PaperStore(args.db)
    rows = store.list_papers(limit=args.limit, status=args.status, sort="relevance_score")
    if not rows:
        print("No papers to review.")
        store.close()
        return 0

    print("Quick Review — keys: t=to-read, r=read, d=dismiss, s=skip, o=open, q=quit")
    for index, row in enumerate(rows, start=1):
        print("\n" + "=" * 78)
        print(f"{index}/{len(rows)}  [{row['relevance_score']:.3f}] {row['title']}")
        print(f"{row['source']} | {row['published_at'] or 'date n/a'} | status={row['status']}")
        print(textwrap.fill(row["abstract"] or "(no abstract)", width=78))
        print(f"URL: {row['url'] or 'n/a'}")
        while True:
            choice = input("Action [t/r/d/s/o/q]: ").strip().lower()
            if choice in {"t", "r", "d", "s", "o", "q"}:
                break
            print("Use t, r, d, s, o or q.")
        if choice == "q":
            break
        if choice == "t":
            store.set_status(row["id"], "to-read")
        elif choice == "r":
            store.set_status(row["id"], "read")
        elif choice == "d":
            reason = input("Dismiss reason (optional): ").strip() or None
            store.set_status(row["id"], "dismissed", dismiss_reason=reason)
        elif choice == "o":
            local_pdf = offline_pdf_path(row)
            if local_pdf.exists():
                webbrowser.open(local_pdf.as_uri())
            else:
                url = row["pdf_url"] or row["url"]
                if url:
                    webbrowser.open(url)
        print()
    store.close()
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    try:
        import uvicorn
        from workspace_web import create_app
    except ImportError as exc:
        print("Web workspace dependencies are missing. Run setup_litradar.bat or install requirements-web.txt.", file=sys.stderr)
        return 2
    host = args.host
    if host not in {"127.0.0.1", "localhost"}:
        print("For safety, the first web workspace release only binds to localhost.", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{args.port}"
    print(f"LitBeacon workspace is available at {url} (local-only). Press Ctrl+C to stop.", flush=True)
    if args.open_browser:
        webbrowser.open(url)
    uvicorn.run(create_app(args.db), host=host, port=args.port, log_level="info")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    try:
        from ui import LitRadarApp
    except ImportError as exc:
        print("The Textual UI is not installed.", file=sys.stderr)
        print("Install it with: python -m pip install -r requirements-ui.txt", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        return 2
    app = LitRadarApp(db_path=args.db)
    app.run()
    return 0


def cmd_ingest_fixture(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    papers = [Paper(**item) for item in data]
    ranked = _rank(papers, profile, semantic=args.semantic)
    store = PaperStore(args.db)
    store.upsert_papers(
        (
            paper,
            score.total,
            score.group_hits,
            score.keyword_score,
            score.semantic_score,
            score.scoring_version,
        )
        for paper, score in ranked
    )
    print(f"Ingested {len(papers)} fixture papers using {ranked[0][1].scoring_version if ranked else 'no scoring'}.")
    store.close()
    return 0


def cmd_assess(args: argparse.Namespace) -> int:
    from llm.assessment import assess_paper
    from llm.providers import make_provider

    profile = _load_profile(args.profile)
    provider = make_provider(args.provider, args.model)
    store = PaperStore(args.db)
    rows = store.list_papers(limit=args.limit, status=args.status, sort="relevance_score")
    assessed = 0
    failed = 0
    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] Assessing: {row['title']}", flush=True)
        paper = Paper(
            source=row["source"],
            title=row["title"],
            abstract=row["abstract"],
            authors=json.loads(row["authors_json"]),
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            doi=row["doi"],
            url=row["url"],
            pdf_url=row["pdf_url"],
            venue=row["venue"],
            citation_count=row["citation_count"],
            external_id=row["external_id"],
            raw=json.loads(row["raw_json"]),
        )
        try:
            score = Score(
                total=row["relevance_score"],
                keyword_score=row["keyword_score"],
                semantic_score=row["semantic_score"],
                group_hits=json.loads(row["matched_groups_json"]),
                scoring_version=row["scoring_version"],
            )
            assessment = assess_paper(provider, paper, score, profile)
            store.set_llm_assessment(row["id"], assessment.as_dict())
            assessed += 1
            print(
                f"[{assessment.overlap_level}] relevance={assessment.relevance:.2f} "
                f"overlap={assessment.potential_overlap:.2f} | {paper.title}"
            )
        except Exception as exc:
            failed += 1
            print(f"id={row['id']} ERROR: {exc}", file=sys.stderr)
    store.close()
    print(f"Assessment complete: {assessed} succeeded, {failed} failed, {len(rows)} attempted.")
    return 0 if assessed else 1


def cmd_explore(args: argparse.Namespace) -> int:
    config = RadarConfig.load()
    store = PaperStore(args.db)
    try:
        def report(event: str, message: str) -> None:
            label = {"started": "FETCH", "completed": "DONE", "cache-hit": "CACHE", "error": "ERROR"}.get(event, event.upper())
            print(f"[{label}] {message}", file=sys.stderr, flush=True)

        result = explore_citation_graph(
            store,
            args.paper_id,
            direction=args.direction,
            depth=args.depth,
            limit=args.limit,
            max_nodes=args.max_nodes,
            config=config,
            refresh=args.refresh,
            profile_path=args.profile,
            progress=report,
        )
        print(f"Citation exploration: {result.root_title} (library id={result.root_id})")
        print(
            f"Discovered {len(result.papers)} other paper(s); stored {result.edges_added} new relation edge(s); "
            f"provider lookups={result.provider_requests}; cache hits={result.cache_hits}; "
            f"depth≤{result.depth_limit}; node cap={result.max_nodes}."
        )
        if result.papers:
            print("\nPapers (stored in the library; use `show ID` or `set-status ID to-read` to triage):")
            for item in result.papers:
                rel = ", ".join(item.via) or "citation graph"
                year = item.year or "year n/a"
                doi = f" | DOI {item.doi}" if item.doi else ""
                groups = f" | profile={','.join(item.matched_groups[:4])}" if item.matched_groups else ""
                print(f"  id={item.paper_id} | score={item.relevance_score:.3f} (keyword={item.keyword_score:.3f}) | depth={item.depth} | links={item.graph_links} | {rel} | {year} | citations={item.citation_count} | {item.title}{doi}{groups}")
                if item.url:
                    print(f"      {item.url}")
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if result.errors and not result.papers:
            return 1
        if not result.papers and result.provider_requests == 0 and result.cache_hits == 0:
            return 1
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_config(args: argparse.Namespace) -> int:
    config = RadarConfig.load()
    print(json.dumps(config.masked_dict(), ensure_ascii=False, indent=2))
    return 0


def _report_progress(event: str, message: str) -> None:
    label = {"started": "START", "completed": "DONE", "cache-hit": "CACHE", "error": "ERROR", "warning": "WARN"}.get(event, event.upper())
    print(f"[{label}] {message}", flush=True)


def cmd_scan(args: argparse.Namespace) -> int:
    try:
        result = run_scheduled_scan(
            db_path=args.db,
            profile_path=args.profile,
            config_path=args.config,
            semantic=args.semantic,
            progress=_report_progress,
        )
    except (ValueError, OSError) as exc:
        print(f"Scheduled scan could not start: {exc}", file=sys.stderr)
        return 2
    print(
        f"Scan run #{result.run_id}: {result.query_count} query/queries; fetched {result.fetched}; "
        f"new papers {result.newly_stored}; library total {result.library_total}."
    )
    for error in result.errors:
        print(f"WARNING: {error}", file=sys.stderr)
    # A partial provider failure should be visible, but does not discard the
    # successful source results. Return failure only if every scan failed.
    return 1 if result.errors and result.fetched == 0 else 0


def cmd_digest(args: argparse.Namespace) -> int:
    try:
        # Manual --send must load the local .env too; scheduled-run does this
        # before entering cmd_digest, but direct CLI calls do not.
        if args.send:
            RadarConfig.load()
        config_path = args.config
        output_path: Path | None = Path(args.output) if args.output else None
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        digest_settings = config.get("digest", {}) if isinstance(config, dict) else {}
        limit = args.limit if args.limit is not None else int(digest_settings.get("limit", 15))
        queue_limit = args.queue_limit if args.queue_limit is not None else int(digest_settings.get("queue_limit", 5))
        channel = "telegram" if args.send else "preview"
        result = build_digest(
            db_path=args.db,
            period=args.period,
            since=args.since,
            limit=limit,
            queue_limit=queue_limit,
            config_path=config_path,
            channel=channel,
        )
        if output_path:
            if not output_path.is_absolute():
                output_path = (ROOT / output_path).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.text, encoding="utf-8")
            print(f"Digest written to: {output_path}")
        elif not args.send:
            print(result.text)

        status = "preview"
        sent_at = None
        error_message = ""
        if args.send:
            try:
                message_count = send_telegram(result.text)
                status = "sent"
                sent_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                print(f"Telegram delivery succeeded ({message_count} message(s)).")
            except (ValueError, RuntimeError) as exc:
                status = "failed"
                error_message = str(exc)
                print(f"Telegram delivery failed: {error_message}", file=sys.stderr)
        store = PaperStore(args.db)
        try:
            store.record_digest_delivery(
                channel="telegram" if args.send else "preview",
                period=args.period,
                generated_at=result.generated_at,
                sent_at=sent_at,
                since_at=result.since,
                paper_ids=result.paper_ids,
                output_path=str(output_path or ""),
                status=status,
                error_message=error_message,
            )
        finally:
            store.close()
        if args.send and status != "sent":
            return 1
        print(f"Digest covers {len(result.paper_ids)} paper(s); possible-overlap signals: {result.warnings_count}.")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Could not generate digest: {exc}", file=sys.stderr)
        return 2


def _write_job_enablement(config_path: str | Path, action: str, job: str, *, frequency: str = "daily", when: str = "08:00") -> None:
    """Persist whether a scheduled job is desired, even on OSes with manual cron setup."""
    path = Path(config_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    selected = ("scan", "digest") if job == "all" else (job,)
    for selected_job in selected:
        if selected_job == "scan":
            payload.setdefault("scan", {})["enabled"] = action == "install"
        elif selected_job == "digest":
            delivery = payload.setdefault("delivery", {})
            delivery["enabled"] = action == "install"
            if action == "install":
                delivery["frequency"] = frequency
                delivery["time"] = when
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_scheduled_run(args: argparse.Namespace) -> int:
    try:
        schedule_config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        schedule_config = {}
    job_settings = schedule_config.get("scan" if args.job == "scan" else "delivery", {})
    if isinstance(job_settings, dict) and job_settings.get("enabled", True) is False:
        print(f"Scheduled job '{args.job}' is disabled in {args.config}; skipping.")
        return 0
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"scheduled-{args.job}.log"
    exit_code = 0
    with log_path.open("a", encoding="utf-8") as log:
        with redirect_stdout(log), redirect_stderr(log):
            print("\n" + "=" * 72)
            print(f"Scheduled LitBeacon job={args.job} at {datetime.now(timezone.utc).isoformat()}")
            try:
                if args.job == "scan":
                    nested = argparse.Namespace(
                        db=args.db, profile=args.profile, config=args.config, semantic=None,
                    )
                    exit_code = cmd_scan(nested)
                else:
                    # RadarConfig.load() loads this installation's .env without
                    # overriding environment variables set by the OS scheduler.
                    RadarConfig.load()
                    configured = bool(os.getenv("LITRADAR_TELEGRAM_BOT_TOKEN") and os.getenv("LITRADAR_TELEGRAM_CHAT_ID"))
                    report_name = f"digest-{args.period}-{datetime.now().strftime('%Y-%m-%d')}.md"
                    nested = argparse.Namespace(
                        db=args.db, profile=args.profile, config=args.config, period=args.period,
                        since=None, limit=None, queue_limit=None,
                        output=str(Path("reports") / report_name), send=configured,
                    )
                    exit_code = cmd_digest(nested)
                    if not configured:
                        print("Telegram is not configured; the digest was saved locally only.")
                print(f"Job exit code: {exit_code}")
            except Exception as exc:
                print(f"Scheduled job crashed: {type(exc).__name__}: {exc}")
                exit_code = 1
    print(f"Scheduled {args.job} job finished with exit code {exit_code}. Log: {log_path}")
    return exit_code


def cmd_schedule(args: argparse.Namespace) -> int:
    if args.action == "remove":
        # Disable at application level too: stale cron/launchd entries become harmless.
        _write_job_enablement(args.config, "remove", args.job, frequency=args.frequency, when=args.time)
        if os.name != "nt":
            print(f"Disabled scheduled-run configuration for {args.job}. Remove the corresponding cron/launchd entry manually if one exists.")
            return 0
    if os.name != "nt":
        print("Windows Task Scheduler install/status is only available on Windows. On Linux/macOS, use cron/launchd and `python cli.py schedule remove --job scan|digest|all` to disable stale jobs safely.", file=sys.stderr)
        return 2
    if not SOURCE_CHECKOUT:
        print("Windows Task Scheduler setup requires the source checkout and Windows launchers; wheel installations support manual scheduled-run only.", file=sys.stderr)
        return 2
    script = CODE_ROOT / "schedule_litradar.ps1"
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-Action", args.action, "-TaskSet", args.job, "-Frequency", args.frequency, "-Time", args.time,
    ]
    try:
        code = subprocess.run(command, cwd=ROOT, check=False).returncode
        if code == 0 and args.action == "install":
            _write_job_enablement(args.config, "install", args.job, frequency=args.frequency, when=args.time)
        return code
    except OSError as exc:
        print(f"Could not invoke Windows Task Scheduler helper: {exc}", file=sys.stderr)
        return 1


def cmd_telegram_run(args: argparse.Namespace) -> int:
    try:
        with configure_listener_logging(debug=getattr(args, "debug", False),
                                        log_file=getattr(args, "log_file", None)):
            logger = logging.getLogger("litradar.telegram")
            try:
                # Load project .env only for this explicitly invoked optional listener.
                RadarConfig.load()
                token = os.getenv("LITRADAR_TELEGRAM_BOT_TOKEN", "").strip()
                chat_id = os.getenv("LITRADAR_TELEGRAM_CHAT_ID", "").strip()
                if not token or not chat_id:
                    logger.error("Telegram listener requires LITRADAR_TELEGRAM_BOT_TOKEN and "
                                 "LITRADAR_TELEGRAM_CHAT_ID. Configure them locally before starting.")
                    return 2
                bot = LitRadarTelegramBot(token=token, chat_id=chat_id, config_path=args.config,
                                          db_path=args.db, profile_path=args.profile)
                bot.run_forever(timeout=args.poll_timeout)
                return 0
            except TelegramAPIError:
                # The listener has already logged a bounded, actionable diagnostic.
                return 2
            except KeyboardInterrupt:
                logger.info("Telegram listener stopped by user.")
                return 0
            except Exception:
                logger.error("Telegram listener could not start or continue. Check local configuration, "
                             "file permissions and available disk space; private error details are omitted.")
                return 2
    except (ValueError, OSError):
        print("Could not initialize Telegram diagnostics. Choose a writable log file and check its directory permissions.",
              file=sys.stderr)
        return 2


def cmd_telegram_chats(args: argparse.Namespace) -> int:
    try:
        # telegram_chat_ids reads os.environ, so load the project .env first.
        RadarConfig.load()
        chats = telegram_chat_ids()
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not chats:
        print("No chats found. Open your bot in Telegram, press Start or send /start, then run this command again.")
        return 0
    print("Recent chats that have sent an update to this bot:")
    for item in chats:
        print(f"chat_id={item['chat_id']} | type={item['type']} | label={item['label']}")
    print("Put the intended chat_id into LITRADAR_TELEGRAM_CHAT_ID in .env. Message content is not displayed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    epilog = """
Examples:
  python cli.py init
  python cli.py search "adaptive context emotion sarcasm"
  python cli.py venue lookup "Computational Linguistics"
  python cli.py venue search SOURCE_ID "emotion context" --year-from 2023 --year-to 2026
  python cli.py evidence show 42
  python cli.py evidence export 42 --output matrix.md
  python cli.py config
  python cli.py list --status new --sort recent
  python cli.py list --sort personalized --limit 20
  python cli.py list --query "context selection" --min-score 0.80
  python cli.py show 42
  python cli.py explore 42 --direction all --depth 1
  python cli.py scan
  python cli.py digest --period weekly --output reports/weekly.md
  python cli.py schedule install --job scan --frequency daily --time 08:00
  python cli.py schedule install --job digest --frequency weekly --time 09:00
  python cli.py schedule remove --job digest   # remove only digest; scan remains
  python cli.py schedule remove --job all      # remove both scheduled jobs
  python cli.py web                          # start browser workspace on localhost
  python cli.py telegram-chats
  python cli.py telegram-run
  python cli.py set-status 42 to-read
  python cli.py dismiss 42 --reason irrelevant
  python cli.py feedback 42 positive --reason useful
  python cli.py list --sort personalized --limit 20
  python cli.py list --sort influential_citations
  python cli.py restore 42
  python cli.py review --status new
  python cli.py ui
  python cli.py export-bibtex 42 --output paper.bib
  python cli.py export-bibtex --status read --output read.bib
  python cli.py note 42 --edit
  python cli.py export-notes --status read --output literature_review_draft.md
  python cli.py download 42
  python cli.py download --status to-read --limit 10

Most commands have their own help page, e.g.:
  python cli.py list --help
  python cli.py search --help
  python cli.py venue --help
  python cli.py evidence --help
  python cli.py ui --help
  python cli.py explore --help
  python cli.py scan --help
  python cli.py digest --help
  python cli.py schedule --help
"""
    parser = argparse.ArgumentParser(
        description=f"LitBeacon {VERSION} (formerly LitRadar) — personal literature research workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(epilog),
    )
    parser.add_argument("--version", action="version", version=f"LitBeacon {VERSION} (formerly LitRadar)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    from venue_cli import register_commands
    register_commands(sub)

    p_init = sub.add_parser("init", help="initialize or migrate the database")
    p_init.set_defaults(func=cmd_init)

    p_backup = sub.add_parser("library-backup", help="consistent local SQLite snapshot; no source migrations")
    p_backup.add_argument("destination", help="new backup directory; parent must exist")
    p_backup.add_argument("--research-dir", help="explicitly include this stopped-writer research artifact root")
    p_backup.add_argument("--offline-dir", help="explicitly include this stopped-writer offline artifact root")
    p_backup.add_argument("--writers-stopped", action="store_true", help="acknowledge all artifact writers have been stopped")
    p_backup.set_defaults(func=cmd_library_backup)

    p_library_restore = sub.add_parser("library-restore", help="verify a trusted bundle and restore into a new directory only")
    p_library_restore.add_argument("bundle", help="local backup bundle directory")
    p_library_restore.add_argument("destination", help="new restore directory; never overwrite or merge")
    p_library_restore.set_defaults(func=cmd_library_restore)

    p_config = sub.add_parser("config", help="show effective runtime configuration (secrets are masked)")
    p_config.set_defaults(func=cmd_config)

    p_scan = sub.add_parser("scan", help="run all configured scheduled topic searches and store new papers")
    p_scan.add_argument("--config", default=str(DEFAULT_SCAN_CONFIG), help="digest/scheduled scan JSON configuration")
    p_scan.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research ranking profile JSON")
    p_scan.add_argument("--semantic", action=argparse.BooleanOptionalAction, default=None, help="override scan.semantic in config; default is keyword-only for lightweight background scans")
    p_scan.set_defaults(func=cmd_scan)

    p_digest = sub.add_parser("digest", help="preview or deliver a daily/weekly research digest")
    p_digest.add_argument("--period", choices=["daily", "weekly"], default="weekly")
    p_digest.add_argument("--since", help="explicit inclusive ISO date/time start; otherwise uses last successful Telegram delivery or period window")
    p_digest.add_argument("--limit", type=int, help="maximum new papers to include; defaults to digest.limit in config")
    p_digest.add_argument("--queue-limit", type=int, help="reading-queue items to include; defaults to digest.queue_limit in config")
    p_digest.add_argument("--config", default=str(DEFAULT_SCAN_CONFIG), help="digest/scheduled scan JSON configuration")
    p_digest.add_argument("--output", help="write a Markdown digest to this path")
    p_digest.add_argument("--send", action="store_true", help="send the digest through Telegram (requires token and chat id in .env)")
    p_digest.set_defaults(func=cmd_digest)

    p_scheduled = sub.add_parser("scheduled-run", help="one-shot entry point used by Windows Task Scheduler/cron")
    p_scheduled.add_argument("--job", choices=["scan", "digest"], required=True)
    p_scheduled.add_argument("--period", choices=["daily", "weekly"], default="weekly")
    p_scheduled.add_argument("--profile", default=str(DEFAULT_PROFILE))
    p_scheduled.add_argument("--config", default=str(DEFAULT_SCAN_CONFIG))
    p_scheduled.set_defaults(func=cmd_scheduled_run)

    p_schedule = sub.add_parser("schedule", help="install/remove/check Windows Task Scheduler jobs")
    p_schedule.add_argument("action", choices=["install", "remove", "status"])
    p_schedule.add_argument("--job", choices=["scan", "digest", "all"], default="all")
    p_schedule.add_argument("--frequency", choices=["daily", "weekly"], default="daily")
    p_schedule.add_argument("--time", default="08:00", help="local 24-hour time HH:MM")
    p_schedule.add_argument("--config", default=str(DEFAULT_SCAN_CONFIG), help="persist desired scan/digest state in config")
    p_schedule.set_defaults(func=cmd_schedule)

    p_telegram = sub.add_parser("telegram-chats", help="list chat IDs from recent Telegram bot updates; message contents are not shown")
    p_telegram.set_defaults(func=cmd_telegram_chats)

    p_telegram_run = sub.add_parser("telegram-run", help="listen for private Telegram bot commands (keep this process running)")
    p_telegram_run.add_argument("--config", default=str(DEFAULT_SCAN_CONFIG), help="digest/scheduled scan JSON configuration")
    p_telegram_run.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research profile JSON")
    p_telegram_run.add_argument("--poll-timeout", type=int, default=25, help="Telegram long-poll timeout in seconds (0–25)")
    p_telegram_run.add_argument("--debug", action="store_true", help="include safe listener API timing/outcome diagnostics (no request/response contents)")
    p_telegram_run.add_argument("--log-file", type=Path, help="append UTF-8 listener diagnostics to a rotating local file (1 MiB, 3 backups)")
    p_telegram_run.set_defaults(func=cmd_telegram_run)

    p_search = sub.add_parser("search", help="search sources, score papers, and store results")
    p_search.add_argument("query", nargs="?", help="search query")
    p_search.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research profile JSON")
    p_search.add_argument("--sources", nargs="+", help="registered providers; defaults to LITRADAR_SOURCES")
    p_search.add_argument("--per-source", type=int, default=20, help="papers requested from each source")
    p_search.add_argument("--limit", type=int, default=15, help="number of fetched papers to print")
    p_search.add_argument("--semantic", action=argparse.BooleanOptionalAction, default=True, help="use sentence-transformer semantic scoring")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="browse papers stored in SQLite")
    p_list.add_argument("--limit", type=int, default=50, help="maximum number of papers to show")
    p_list.add_argument("--status", choices=["all", *STATUSES], default="all", help="filter by workflow status")
    p_list.add_argument("--query", help="full-text search title, abstract, venue, or personal notes (FTS5 when available)")
    p_list.add_argument("--tag", help="filter by tag")
    p_list.add_argument("--min-score", type=float, help="minimum relevance score")
    p_list.add_argument("--sort", choices=SORT_CHOICES, default="relevance_score")
    p_list.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research profile JSON (used by personalized sort)")
    p_list.set_defaults(func=cmd_list)

    p_top = sub.add_parser("top", help="show stored papers ranked by score")
    p_top.add_argument("limit", type=int, nargs="?", default=10)
    p_top.add_argument("--sort", choices=SORT_CHOICES, default="relevance_score")
    p_top.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research profile JSON (used by personalized sort)")
    p_top.set_defaults(func=cmd_top)

    p_recent = sub.add_parser("recent", help="show the most recently published stored papers")
    p_recent.add_argument("limit", type=int, nargs="?", default=10)
    p_recent.set_defaults(func=cmd_recent)

    p_stats = sub.add_parser("stats", help="show library counts by workflow status")
    p_stats.set_defaults(func=cmd_stats)

    p_show = sub.add_parser("show", help="show one stored paper in detail")
    p_show.add_argument("paper_id", type=int)
    p_show.set_defaults(func=cmd_show)

    p_explore = sub.add_parser(
        "explore", help="discover and store a bounded citation neighborhood around a paper"
    )
    p_explore.add_argument("paper_id", type=int, help="ID of the seed paper in the local library")
    p_explore.add_argument(
        "--direction", choices=["both", "references", "cited-by", "related", "all"], default="both",
        help="follow references, papers citing the seed, related works, or combinations",
    )
    p_explore.add_argument("--depth", type=int, choices=[1, 2], default=1, help="graph traversal depth (max 2)")
    p_explore.add_argument("--limit", type=int, default=20, help="maximum papers per direction and provider (1-100)")
    p_explore.add_argument("--max-nodes", type=int, default=50, help="maximum unique nodes in this traversal (1-200)")
    p_explore.add_argument("--refresh", action="store_true", help="bypass the local citation cache")
    p_explore.add_argument("--profile", default=str(DEFAULT_PROFILE), help="research ranking profile for newly discovered papers")
    p_explore.set_defaults(func=cmd_explore)

    p_status = sub.add_parser("set-status", help="change a paper's workflow status")
    p_status.add_argument("paper_id", type=int)
    p_status.add_argument("status", choices=STATUSES)
    p_status.set_defaults(func=cmd_set_status)

    p_dismiss = sub.add_parser("dismiss", help="hide a paper from normal views without deleting it")
    p_dismiss.add_argument("paper_id", type=int)
    p_dismiss.add_argument("--reason", choices=["irrelevant", "duplicate", "too broad", "wrong domain", "already known", "other"])
    p_dismiss.set_defaults(func=cmd_dismiss)

    p_feedback = sub.add_parser("feedback", help="record explicit positive/negative feedback for personalization")
    p_feedback.add_argument("paper_id", type=int)
    p_feedback.add_argument("signal", choices=["positive", "negative"])
    p_feedback.add_argument("--reason", default="", help="optional reason, e.g. useful, irrelevant, too broad")
    p_feedback.set_defaults(func=cmd_feedback)

    p_restore = sub.add_parser("restore", help="restore a dismissed/archived paper")
    p_restore.add_argument("paper_id", type=int)
    p_restore.add_argument("--status", choices=["new", "to-read"], default="new")
    p_restore.set_defaults(func=cmd_restore)

    p_tags = sub.add_parser("tags", help="add, remove, or replace tags on a paper")
    p_tags.add_argument("paper_id", type=int)
    p_tags.add_argument("tags", nargs="*", help="tags to add")
    p_tags.add_argument("--remove", nargs="+", help="tags to remove")
    p_tags.add_argument("--set", dest="set_tags", help="replace all tags; comma-separated")
    p_tags.set_defaults(func=cmd_tags)

    p_note = sub.add_parser("note", help="set a free-text note on a paper")
    p_note.add_argument("paper_id", type=int)
    p_note.add_argument("text", nargs="?", help="replacement note text")
    p_note.add_argument("--edit", action="store_true", help="open existing notes or structured template in $EDITOR/VISUAL")
    p_note.set_defaults(func=cmd_note)

    p_export_notes = sub.add_parser("export-notes", help="export paper metadata, abstracts, and personal notes as Markdown")
    p_export_notes.add_argument("--status", choices=["all", *STATUSES], default="read", help="library view to export")
    p_export_notes.add_argument("--output", default="literature_review_draft.md", help="output Markdown file")
    p_export_notes.set_defaults(func=cmd_export_notes)

    p_bib = sub.add_parser("export-bibtex", help="export one or more papers or a status view to a .bib file")
    p_bib.add_argument("paper_ids", nargs="*", type=int, help="paper IDs; omit to export a filtered library view")
    p_bib.add_argument("--status", choices=["all", *STATUSES], default="all", help="status filter when no paper IDs are given")
    p_bib.add_argument("--output", default="litradar.bib", help="output .bib file")
    p_bib.set_defaults(func=cmd_export_bibtex)

    p_download = sub.add_parser("download", help="save metadata, abstract, and available PDF for offline use")
    p_download.add_argument("paper_ids", nargs="*", type=int, help="paper IDs; omit to download a filtered library view")
    p_download.add_argument("--status", choices=["all", "new", "to-read", "read", "archived"], default="to-read", help="status filter when no IDs are given")
    p_download.add_argument("--limit", type=int, default=10, help="maximum papers to save in bulk mode")
    p_download.add_argument("--output-dir", default=str(DEFAULT_OFFLINE_DIR), help="directory for offline paper folders")
    p_download.set_defaults(func=cmd_download)

    p_open = sub.add_parser("open", help="open a paper URL in the default browser")
    p_open.add_argument("paper_id", type=int)
    p_open.set_defaults(func=cmd_open)

    p_review = sub.add_parser("review", help="quickly triage papers in the terminal")
    p_review.add_argument("--limit", type=int, default=20)
    p_review.add_argument("--status", choices=["new", "to-read", "all"], default="new")
    p_review.set_defaults(func=cmd_review)

    p_ui = sub.add_parser("ui", help="launch the optional Textual terminal UI")
    p_ui.set_defaults(func=cmd_ui)

    p_web = sub.add_parser("web", help="launch the optional browser research workspace (localhost only)")
    p_web.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"], help="bind address; external interfaces are intentionally disabled")
    p_web.add_argument("--port", type=int, default=8765, help="local web port")
    p_web.add_argument("--open-browser", action=argparse.BooleanOptionalAction, default=True, help="open the workspace in the default browser")
    p_web.set_defaults(func=cmd_web)

    p_fixture = sub.add_parser("ingest-fixture", help="ingest local JSON fixture papers")
    p_fixture.add_argument("file")
    p_fixture.add_argument("--profile", default=str(DEFAULT_PROFILE))
    p_fixture.add_argument("--semantic", action=argparse.BooleanOptionalAction, default=True)
    p_fixture.set_defaults(func=cmd_ingest_fixture)

    p_assess = sub.add_parser("assess", help="[experimental] run LLM triage on stored papers")
    p_assess.add_argument("--profile", default=str(DEFAULT_PROFILE))
    p_assess.add_argument("--provider", choices=["openai", "anthropic", "ollama"], default="ollama")
    p_assess.add_argument("--model", default=None)
    p_assess.add_argument("--limit", type=int, default=5)
    p_assess.add_argument("--status", choices=["all", *STATUSES], default="all", help="only assess papers in this status")
    p_assess.set_defaults(func=cmd_assess)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    ensure_user_defaults()
    raise SystemExit(args.func(args))
