"""Local-only browser workspace for LitBeacon (legacy package name: LitRadar).

The first web release intentionally uses FastAPI + the existing SQLite store and
vanilla browser JavaScript/SVG. It has no frontend package manager or external CDN
requirement, so the shipped workspace works on a typical desktop installation.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from storage.sqlite import PaperStore, STATUSES

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
STATIC_ROOT = WEB_ROOT / "static"
DEFAULT_DB = ROOT / "data" / "litradar.sqlite3"


class PaperPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = None
    notes: str | None = Field(default=None, max_length=50_000)
    tags: list[str] | None = None


def _load_json(value: Any, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def _paper_dict(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    return {
        "id": int(row["id"]),
        "title": str(row["title"] or ""),
        "abstract": str(row["abstract"] or ""),
        "authors": _load_json(row["authors_json"], []),
        "source": str(row["source"] or ""),
        "doi": row["doi"],
        "url": row["url"],
        "published_at": row["published_at"],
        "venue": row["venue"],
        "citation_count": int(row["citation_count"] or 0),
        "reference_count": row["reference_count"] if "reference_count" in keys else None,
        "relevance_score": round(float(row["relevance_score"] or 0), 4),
        "semantic_score": row["semantic_score"] if "semantic_score" in keys else None,
        "status": str(row["status"] or "new"),
        "tags": _load_json(row["tags_json"], []),
        "notes": str(row["notes"] or ""),
        "created_at": row["created_at"],
    }


def _with_store(db_path: str | Path):
    """Tiny context helper to keep each request's SQLite connection short-lived."""
    class StoreContext:
        def __enter__(self) -> PaperStore:
            self.store = PaperStore(db_path)
            return self.store
        def __exit__(self, exc_type, exc, tb) -> None:
            self.store.close()
    return StoreContext()


def _make_clusters(rows: list[sqlite3.Row]) -> dict[str, Any]:
    """Build explicitly heuristic reading clusters, not pretend-semantic labels."""
    if not rows:
        return {"method": "heuristic", "description": "Groups are based on tags, venue and shared title terms.", "clusters": []}

    prepared = [_paper_dict(row) for row in rows]
    tag_counts: Counter[str] = Counter()
    venue_counts: Counter[str] = Counter()
    for paper in prepared:
        for tag in paper["tags"]:
            if isinstance(tag, str) and tag.strip():
                tag_counts[tag.strip()] += 1
        venue = str(paper.get("venue") or "").strip()
        if venue:
            venue_counts[venue] += 1

    stop = {
        "this", "that", "with", "from", "using", "based", "into", "their", "these", "those", "have", "has", "were", "been", "between", "through", "about", "across", "toward", "towards", "under", "over", "study", "paper", "approach", "method", "methods", "analysis", "model", "models", "data", "using", "results", "show", "new", "for", "and", "the", "a", "an", "of", "in", "on", "to", "by", "as", "is", "are", "or", "we", "our", "can", "may", "not", "via", "its", "it", "their", "which", "when", "what", "how", "why", "who", "than", "more", "less", "toward", "towards"
    }
    term_docs: Counter[str] = Counter()
    paper_terms: list[Counter[str]] = []
    for paper in prepared:
        text = f"{paper['title']} {paper['abstract'][:1500]}".casefold()
        terms = Counter(token for token in re.findall(r"[a-z][a-z0-9-]{3,}", text) if token not in stop)
        paper_terms.append(terms)
        term_docs.update(terms.keys())
    candidate_terms = {term for term, count in term_docs.items() if count >= 2 and count <= max(2, int(len(prepared) * 0.65))}

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assigned_method: Counter[str] = Counter()
    for paper, terms in zip(prepared, paper_terms):
        matching_tags = [str(tag).strip() for tag in paper["tags"] if isinstance(tag, str) and str(tag).strip()]
        if matching_tags:
            label, method = f"Tag · {matching_tags[0]}", "tags"
        elif paper.get("venue") and venue_counts[str(paper["venue"])] >= 2:
            label, method = f"Venue · {paper['venue']}", "venue"
        else:
            scored = sorted(
                ((term, count * (1 + (len(prepared) / term_docs[term]))) for term, count in terms.items() if term in candidate_terms),
                key=lambda item: (-item[1], item[0]),
            )
            if scored:
                label, method = f"Topic · {scored[0][0]}", "shared-title-abstract-terms"
            else:
                label, method = "Unclustered", "fallback"
        groups[label].append(paper)
        assigned_method[method] += 1

    clusters = [
        {"label": label, "size": len(papers), "method": (
            "user tag" if label.startswith("Tag · ") else "shared venue" if label.startswith("Venue · ") else
            "shared title/abstract terms" if label.startswith("Topic · ") else "no repeated local signal"
        ), "papers": papers[:30]}
        for label, papers in groups.items()
    ]
    clusters.sort(key=lambda item: (-item["size"], item["label"].casefold()))
    return {
        "method": "heuristic",
        "description": "Exploratory groups use existing tags, repeated venues, and shared title/abstract terms. They are not embedding-based semantic clusters.",
        "clusters": clusters[:30],
    }


def create_app(db_path: str | Path = DEFAULT_DB) -> FastAPI:
    app = FastAPI(title="LitBeacon Research Workspace", version="0.8.0")
    app.state.db_path = str(db_path)
    app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "product": "LitBeacon", "legacy_name": "LitRadar", "database": Path(app.state.db_path).name}

    @app.get("/api/summary")
    def summary() -> dict[str, Any]:
        with _with_store(app.state.db_path) as store:
            stats = store.stats()
            recent = store.list_papers(limit=8, sort="newest_added")
            to_read = store.list_papers(limit=8, status="to-read", sort="relevance_score")
            return {
                "stats": stats,
                "recent": [_paper_dict(row) for row in recent],
                "reading_queue": [_paper_dict(row) for row in to_read],
            }

    @app.get("/api/papers")
    def papers(
        q: str = Query(default="", max_length=300),
        status: str = "all",
        sort: str = "relevance_score",
        limit: int = Query(default=100, ge=1, le=200),
        tag: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"all", *STATUSES}:
            raise HTTPException(status_code=422, detail="Unsupported status filter")
        if sort == "personalized":
            sort = "relevance_score"
        try:
            with _with_store(app.state.db_path) as store:
                rows = store.list_papers(limit=limit, status=status, query=q or None, sort=sort, tag=tag)
                count = store.total_count(status=status, query=q or None, tag=tag)
                return {"items": [_paper_dict(row) for row in rows], "count": count}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/papers/{paper_id}")
    def paper_detail(paper_id: int) -> dict[str, Any]:
        with _with_store(app.state.db_path) as store:
            row = store.get(paper_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Paper not found")
            return _paper_dict(row)

    @app.patch("/api/papers/{paper_id}")
    def update_paper(paper_id: int, patch: PaperPatch) -> dict[str, Any]:
        if patch.status is not None and patch.status not in STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of: {', '.join(STATUSES)}")
        if patch.tags is not None:
            if len(patch.tags) > 50 or any(len(tag) > 80 for tag in patch.tags):
                raise HTTPException(status_code=422, detail="Use at most 50 tags, each no longer than 80 characters")
            if any(not isinstance(tag, str) for tag in patch.tags):
                raise HTTPException(status_code=422, detail="Tags must be strings")
        with _with_store(app.state.db_path) as store:
            if store.get(paper_id) is None:
                raise HTTPException(status_code=404, detail="Paper not found")
            fields = patch.model_fields_set
            try:
                if "status" in fields and patch.status is not None:
                    store.set_status(paper_id, patch.status)
                if "notes" in fields and patch.notes is not None:
                    store.set_notes(paper_id, patch.notes)
                if "tags" in fields and patch.tags is not None:
                    store.set_tags(paper_id, patch.tags)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="Paper not found") from exc
            row = store.get(paper_id)
            assert row is not None
            return _paper_dict(row)

    @app.get("/api/graph")
    def graph(
        seed_id: int | None = None,
        depth: int = Query(default=1, ge=1, le=2),
        max_nodes: int = Query(default=80, ge=2, le=200),
        relation: Literal["all", "cites", "related"] = "all",
        provider: str | None = Query(default=None, min_length=1, max_length=80),
    ) -> dict[str, Any]:
        with _with_store(app.state.db_path) as store:
            # Apply edge filters during traversal as well as during serialization.
            filters, filter_params = [], []
            if relation != "all":
                filters.append("relation_type=?")
                filter_params.append(relation)
            if provider is not None:
                filters.append("provider=?")
                filter_params.append(provider)
            suffix = (" AND " + " AND ".join(filters)) if filters else ""

            def relations_for(ids, *, induced=False):
                ordered = sorted(ids)
                marks = ",".join("?" for _ in ordered)
                operator = "AND" if induced else "OR"
                return store.conn.execute(
                    f"SELECT * FROM paper_relations WHERE (source_paper_id IN ({marks}) "
                    f"{operator} target_paper_id IN ({marks})){suffix} "
                    "ORDER BY source_paper_id, target_paper_id, relation_type, provider",
                    (*ordered, *ordered, *filter_params),
                ).fetchall()

            providers = [row[0] for row in store.conn.execute(
                "SELECT DISTINCT provider FROM paper_relations ORDER BY provider"
            )]
            truncated = False
            if seed_id is None:
                rows = store.list_papers(limit=max_nodes + 1, sort="relevance_score")
                truncated = len(rows) > max_nodes
                rows = rows[:max_nodes]
                ids = {int(row["id"]) for row in rows}
            else:
                seed = store.get(seed_id)
                if seed is None:
                    raise HTTPException(status_code=404, detail="Paper not found")
                ids: set[int] = {seed_id}
                frontier = {seed_id}
                for _ in range(depth):
                    if not frontier:
                        break
                    relations = relations_for(frontier)
                    next_frontier: set[int] = set()
                    for edge in relations:
                        source_id, target_id = int(edge["source_paper_id"]), int(edge["target_paper_id"])
                        for neighbor in (source_id, target_id):
                            if neighbor not in ids:
                                if store.get(neighbor) is not None:
                                    if len(ids) < max_nodes:
                                        ids.add(neighbor)
                                        next_frontier.add(neighbor)
                                    else:
                                        truncated = True
                    frontier = next_frontier
            edges = relations_for(ids, induced=True) if ids else []
            if ids:
                marks = ",".join("?" for _ in ids)
                paper_rows = store.conn.execute(f"SELECT * FROM papers WHERE id IN ({marks}) ORDER BY id", tuple(ids)).fetchall()
            else:
                paper_rows = []
            nodes = [_paper_dict(row) for row in paper_rows]
            grouped = {}
            for edge in edges:
                source, target = int(edge["source_paper_id"]), int(edge["target_paper_id"])
                if edge["relation_type"] == "related":
                    source, target = sorted((source, target))
                key = (source, target, edge["relation_type"])
                if key not in grouped:
                    grouped[key] = {
                        "source": str(source), "target": str(target), "type": edge["relation_type"],
                        "provider": edge["provider"], "providers": [], "provenance": [],
                    }
                item = grouped[key]
                if edge["provider"] not in item["providers"]:
                    item["providers"].append(edge["provider"])
                item["provenance"].append({"provider": edge["provider"], "observed_at": edge["observed_at"]})
            edge_payload = [grouped[key] for key in sorted(grouped)]
            return {"seed_id": seed_id, "depth": depth, "truncated": truncated, "nodes": nodes,
                    "edges": edge_payload, "providers": providers, "relation": relation, "provider": provider}

    @app.get("/api/clusters")
    def clusters(limit: int = Query(default=400, ge=1, le=500)) -> dict[str, Any]:
        with _with_store(app.state.db_path) as store:
            rows = store.list_papers(limit=limit, sort="relevance_score")
            return _make_clusters(rows)

    @app.get("/api/jobs")
    def jobs() -> dict[str, Any]:
        config_path = ROOT / "digest_config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
        return {
            "platform": "windows" if __import__("os").name == "nt" else "unix",
            "scan_enabled": bool(config.get("scan", {}).get("enabled", True)),
            "digest_enabled": bool(config.get("delivery", {}).get("enabled", True)),
            "delivery": config.get("delivery", {}),
            "note": "Task Scheduler details are available on Windows. On Unix-like systems use cron/launchd and the schedule remove command disables stale scheduled-run jobs safely.",
        }

    @app.post("/api/jobs/install-defaults")
    def install_default_jobs() -> dict[str, Any]:
        import subprocess
        import sys
        commands = [
            [sys.executable, str(ROOT / "cli.py"), "schedule", "install", "--job", "scan", "--frequency", "daily", "--time", "07:30"],
            [sys.executable, str(ROOT / "cli.py"), "schedule", "install", "--job", "digest", "--frequency", "weekly", "--time", "09:00"],
        ]
        outputs: list[str] = []
        for command in commands:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
            output = (completed.stdout or completed.stderr or "").strip()
            if output:
                outputs.append(output)
            if completed.returncode:
                raise HTTPException(status_code=500, detail="\n".join(outputs) or f"Scheduler exited with {completed.returncode}")
        return {"ok": True, "message": "\n".join(outputs) or "Default jobs installed."}

    @app.post("/api/jobs/{job}/remove")
    def remove_job(job: Literal["scan", "digest", "all"]) -> dict[str, Any]:
        import subprocess
        import sys
        completed = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), "schedule", "remove", "--job", job],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode:
            raise HTTPException(status_code=500, detail=output or f"Scheduler exited with {completed.returncode}")
        return {"ok": True, "job": job, "message": output or f"Removed scheduled job: {job}"}

    return app


app = create_app()
