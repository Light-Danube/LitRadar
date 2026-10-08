from __future__ import annotations

import argparse
import json
import sys
import textwrap
import webbrowser
from pathlib import Path

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.personalization import PersonalizationModel, build_model, neutral_results, score_rows
from ranking.scoring import Score, rank_papers, score_papers_semantic
from bibliography import export_rows
from offline import DEFAULT_OFFLINE_DIR, is_available_offline, offline_pdf_path, save_paper_offline
from sources.base import Paper
from storage.sqlite import PaperStore, SORT_CHOICES, STATUSES

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "litradar.sqlite3"
DEFAULT_PROFILE = ROOT / "research_profile.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


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


def cmd_search(args: argparse.Namespace) -> int:
    config = RadarConfig.load()
    profile = _load_profile(args.profile)
    query = args.query or "adaptive context emotion sarcasm online conversation"
    store = PaperStore(args.db)
    try:
        from sources.registry import search_all_sources

        requested_sources = tuple(args.sources) if args.sources else config.enabled_sources
        source_results, source_errors = search_all_sources(
            query,
            sources=requested_sources,
            per_source=args.per_source,
            config=config,
        )
        all_papers: list[Paper] = []
        for source in requested_sources:
            if source in source_errors:
                print(f"{source}: ERROR: {source_errors[source]}", file=sys.stderr)
                continue
            papers = source_results.get(source, [])
            print(f"{source}: fetched {len(papers)} papers", file=sys.stderr)
            all_papers.extend(papers)

        ranked = _rank(all_papers, profile, semantic=args.semantic)
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

        for index, (paper, score) in enumerate(ranked[: args.limit], start=1):
            _print_scored(index, paper, score)
        return 0 if ranked else 1
    finally:
        store.close()


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


def _print_rows(rows, score_overrides: dict[int, float] | None = None) -> None:
    if not rows:
        print("No papers matched the current view.")
        return
    score_overrides = score_overrides or {}
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
        _print_rows(rows, score_overrides if args.sort == "personalized" else None)
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
        store.set_notes(args.paper_id, args.text)
    except KeyError:
        print(f"Paper not found: {args.paper_id}", file=sys.stderr)
        store.close()
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
    for row in rows:
        result = save_paper_offline(row, args.output_dir)
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
    if not url:
        print("Paper has no URL/PDF URL.", file=sys.stderr)
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
    for row in rows:
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
            print(f"id={row['id']} ERROR: {exc}", file=sys.stderr)
    store.close()
    return 0 if assessed else 1


def cmd_config(args: argparse.Namespace) -> int:
    config = RadarConfig.load()
    print(json.dumps(config.masked_dict(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    epilog = """
Examples:
  python cli.py init
  python cli.py search "adaptive context emotion sarcasm"
  python cli.py config
  python cli.py list --status new --sort recent
  python cli.py list --sort personalized --limit 20
  python cli.py list --query "context selection" --min-score 0.80
  python cli.py show 42
  python cli.py set-status 42 to-read
  python cli.py dismiss 42 --reason irrelevant
  python cli.py feedback 42 positive --reason useful
  python cli.py list --sort personalized --limit 20
  python cli.py restore 42
  python cli.py review --status new
  python cli.py ui
  python cli.py export-bibtex 42 --output paper.bib
  python cli.py export-bibtex --status read --output read.bib
  python cli.py download 42
  python cli.py download --status to-read --limit 10

Most commands have their own help page, e.g.:
  python cli.py list --help
  python cli.py search --help
  python cli.py ui --help
"""
    parser = argparse.ArgumentParser(
        description=f"LitRadar {VERSION} — personal literature radar and research inbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(epilog),
    )
    parser.add_argument("--version", action="version", version=f"LitRadar {VERSION}")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_init = sub.add_parser("init", help="initialize or migrate the database")
    p_init.set_defaults(func=cmd_init)

    p_config = sub.add_parser("config", help="show effective runtime configuration (secrets are masked)")
    p_config.set_defaults(func=cmd_config)

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
    p_list.add_argument("--query", help="search title, abstract, or venue")
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
    p_note.add_argument("text", help="replacement note text")
    p_note.set_defaults(func=cmd_note)

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
    raise SystemExit(args.func(args))
