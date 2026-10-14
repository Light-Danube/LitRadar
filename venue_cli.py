"""CLI handoff for explicit online venue discovery and local evidence editing."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from config import RadarConfig
from storage.sqlite import PaperStore


def cmd_venue(args) -> int:
    from venue_discovery import error_status, lookup, search_and_store
    store = PaperStore(args.db)
    try:
        # Config is loaded only for an explicit online command; tests inject it.
        config = RadarConfig.load()
        print("[START] OpenAlex venue-scoped discovery; no LLM request", file=sys.stderr)
        if args.venue_action == "lookup":
            found = lookup(store, args.query, limit=args.limit, config=config)
            payload = {"status": "ambiguous_venue" if len(found) > 1 else "ok" if found else "zero_results",
                       "venues": [v.to_dict() for v in found],
                       "next_step": "Select a concrete source_id and run venue search. Provider metadata does not certify peer review or indexing."}
        else:
            payload = search_and_store(store, args.query, args.source_id,
                                       year_from=args.year_from, year_to=args.year_to,
                                       limit=args.limit, page=args.page, force=args.refresh, config=config)
            payload["browser_handoff"] = "Open the existing Literature inbox to inspect these paper_ids. Browser venue lookup is planned."
            payload["coverage"] = "One bounded OpenAlex primary-source page; not a complete venue bibliography."
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # Do not echo exception strings containing authenticated provider URLs.
        print(json.dumps({"status": error_status(exc),
                          "message": "Venue discovery failed; check input, network access and provider availability."}), file=sys.stderr)
        return 1
    finally:
        store.close()


def cmd_evidence(args) -> int:
    from storage.evidence import EvidenceStore
    from evidence_matrix import export_csv, export_markdown
    store = PaperStore(args.db)
    try:
        evidence = EvidenceStore(store)
        if args.evidence_action == "show":
            print(json.dumps(evidence.get(args.paper_id), ensure_ascii=False, indent=2))
        elif args.evidence_action == "update":
            path = Path(args.file)
            if path.stat().st_size > 200_000:
                raise ValueError("Evidence input exceeds 200 KB")
            fields = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(fields, dict):
                raise ValueError("Evidence input must be a fields object")
            updated = evidence.update(args.paper_id, fields, expected_revision=args.expected_revision)
            print(json.dumps(updated, ensure_ascii=False, indent=2))
        else:
            if not 1 <= len(args.paper_ids) <= 100:
                raise ValueError("Select 1–100 paper IDs")
            text = export_csv(store, args.paper_ids) if args.format == "csv" else export_markdown(
                store, args.paper_ids, research_question=args.research_question,
                hypothesis=args.hypothesis, disconfirming_evidence=args.disconfirming_evidence)
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"Exported evidence worksheet: {args.output}")
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"Evidence error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


def register_commands(sub):
    venue = sub.add_parser("venue", help="explicit online venue lookup/search (separate from broad search)")
    actions = venue.add_subparsers(dest="venue_action", required=True)
    lookup = actions.add_parser("lookup", help="find concrete venue identities; select by ID, never by name")
    lookup.add_argument("query")
    lookup.add_argument("--limit", type=int, default=10)
    lookup.set_defaults(func=cmd_venue)
    search = actions.add_parser("search", help="retrieve one bounded page within a concrete OpenAlex source")
    search.add_argument("source_id", help="S + digits, selected from venue lookup")
    search.add_argument("query")
    search.add_argument("--year-from", type=int)
    search.add_argument("--year-to", type=int)
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--refresh", action="store_true", help="bypass the local venue cache")
    search.set_defaults(func=cmd_venue)
    matrix = sub.add_parser("evidence", help="local human-editable literature worksheet; no LLM calls")
    edits = matrix.add_subparsers(dest="evidence_action", required=True)
    show = edits.add_parser("show", help="show worksheet shape and current revision")
    show.add_argument("paper_id", type=int)
    show.set_defaults(func=cmd_evidence)
    update = edits.add_parser("update", help="apply a bounded JSON fields object with provenance")
    update.add_argument("paper_id", type=int)
    update.add_argument("file")
    update.add_argument("--expected-revision", required=True, type=int)
    update.set_defaults(func=cmd_evidence)
    export = edits.add_parser("export", help="export selected canonical paper evidence")
    export.add_argument("paper_ids", nargs="+", type=int)
    export.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    export.add_argument("--output", required=True)
    export.add_argument("--research-question", default="")
    export.add_argument("--hypothesis", default="")
    export.add_argument("--disconfirming-evidence", default="")
    export.set_defaults(func=cmd_evidence)
