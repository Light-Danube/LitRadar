from __future__ import annotations

from collections import defaultdict
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.scoring import rank_papers
from sources import openalex, semantic_scholar
from sources.base import Paper
from storage.sqlite import PaperStore

Progress = Callable[[str, str], None]
DIRECTIONS = {"references", "cited-by", "related"}


@dataclass(slots=True)
class ExploredPaper:
    paper_id: int
    depth: int
    via: list[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    doi: str = ""
    citation_count: int = 0
    graph_links: int = 0
    url: str = ""
    relevance_score: float = 0.0
    keyword_score: float = 0.0
    matched_groups: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExploreResult:
    root_id: int
    root_title: str
    papers: list[ExploredPaper]
    edges_added: int
    provider_requests: int
    cache_hits: int
    errors: list[str]
    warnings: list[str]
    max_nodes: int
    depth_limit: int


def _emit(progress: Progress | None, event: str, message: str) -> None:
    if progress:
        try:
            progress(event, message)
        except Exception:
            pass


def _directions(value: str) -> tuple[str, ...]:
    value = value.casefold().strip()
    if value == "both":
        return ("references", "cited-by")
    if value == "all":
        return ("references", "cited-by", "related")
    if value in DIRECTIONS:
        return (value,)
    raise ValueError(f"Unsupported direction {value!r}; choose both, references, cited-by, related, or all")


def _first(values: dict[str, list[str]], key: str) -> str | None:
    candidates = values.get(key) or []
    return candidates[0] if candidates else None


def _provider_identifier(store: PaperStore, paper_id: int, provider: str) -> str | None:
    row = store.get(paper_id)
    if row is None:
        return None
    ids = store.identifiers_for_paper(paper_id)
    if provider == "openalex":
        return _first(ids, "openalex_id") or (_first(ids, "doi") or row["doi"])
    if provider == "semantic_scholar":
        direct = _first(ids, "semantic_scholar_id")
        if direct:
            return direct
        doi = _first(ids, "doi") or row["doi"]
        if doi:
            return f"DOI:{doi}"
        arxiv_id = _first(ids, "arxiv_id")
        if arxiv_id:
            return f"ARXIV:{arxiv_id}"
    return None


def _fetch_provider_neighbors(
    provider: str,
    identifier: str,
    direction: str,
    *,
    limit: int,
    config: RadarConfig,
) -> list[Paper]:
    args = {
        "limit": limit,
        "timeout": config.source_timeout,
        "retries": config.source_retries,
        "backoff": config.source_backoff,
    }
    if provider == "openalex":
        return openalex.fetch_neighbors(identifier, direction, api_key=config.openalex_api_key, **args)
    if provider == "semantic_scholar":
        if direction == "related":
            return []
        return semantic_scholar.fetch_neighbors(
            identifier, direction, api_key=config.semantic_scholar_api_key, **args
        )
    raise ValueError(f"Unsupported citation provider: {provider}")


def _relation_neighbors(store: PaperStore, paper_id: int, direction: str) -> list[int]:
    return list(dict.fromkeys(int(row["id"]) for row in store.relation_neighbors(paper_id, direction)))


def explore_citation_graph(
    store: PaperStore,
    paper_id: int,
    *,
    direction: str = "both",
    depth: int = 1,
    limit: int = 20,
    max_nodes: int = 50,
    config: RadarConfig | None = None,
    refresh: bool = False,
    profile_path: str | Path | None = None,
    progress: Progress | None = None,
) -> ExploreResult:
    """Fetch and persist a bounded citation neighborhood rooted at ``paper_id``.

    Citation direction in SQLite is always ``citing paper -> cited paper``. A
    references request therefore records root -> neighbor, while a cited-by
    request records neighbor -> root. Related-work edges are stored separately
    as undirected pairs. New neighbors become normal library entries, linked by
    DOI/provider identifiers where possible.
    """
    directions = _directions(direction)
    if not 1 <= int(depth) <= 2:
        raise ValueError("depth must be 1 or 2 to keep network work bounded")
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit must be between 1 and 100 papers per direction/provider")
    if not 1 <= int(max_nodes) <= 200:
        raise ValueError("max_nodes must be between 1 and 200")
    root = store.get(int(paper_id))
    if root is None:
        raise ValueError(f"Paper id {paper_id} was not found in this library")
    config = config or RadarConfig.load()
    ttl = int(getattr(config, "citation_cache_ttl", 604800))
    profile_file = Path(profile_path) if profile_path else Path(__file__).resolve().parent / "research_profile.json"
    try:
        profile = KeywordProfile.from_json(profile_file)
    except (OSError, ValueError, KeyError, TypeError):
        # Citation discovery stays usable if the optional ranking profile is damaged.
        profile = None
    root_id = int(root["id"])

    # Root at distance zero. A paper is only expanded once even if several
    # citation paths reach it; all edges remain stored independently.
    depths: dict[int, int] = {root_id: 0}
    # Reserve node slots at ingestion time, before all provider batches have
    # been merged into a frontier. Otherwise one response can store more than
    # max_nodes because depths are assigned only after its edge batch is read.
    reserved_ids: set[int] = {root_id}
    via: dict[int, set[str]] = defaultdict(set)
    frontier = [root_id]
    edges_added = 0
    requests = 0
    cache_hits = 0
    errors: list[str] = []
    warnings: list[str] = []
    processed_fetches: set[tuple[int, str, str]] = set()
    stopped_at_cap = False

    for current_depth in range(int(depth)):
        next_frontier: list[int] = []
        for current_id in frontier:
            if current_depth > 0 and len(depths) >= int(max_nodes):
                stopped_at_cap = True
                break
            current_row = store.get(current_id)
            if current_row is None:
                continue
            for item_direction in directions:
                providers = ["openalex"] if item_direction == "related" else ["openalex", "semantic_scholar"]
                for provider in providers:
                    fetch_key = (current_id, provider, item_direction)
                    if fetch_key in processed_fetches:
                        continue
                    processed_fetches.add(fetch_key)
                    provider_identifier = _provider_identifier(store, current_id, provider)
                    if not provider_identifier:
                        continue
                    if store.has_fresh_citation_fetch(
                        current_id, provider, item_direction, ttl,
                        requested_limit=int(limit), force=refresh,
                    ):
                        cache_hits += 1
                        _emit(progress, "cache-hit", f"{provider} {item_direction}: using stored graph edges")
                        continue

                    _emit(progress, "started", f"{provider} {item_direction}: paper id {current_id}")
                    requests += 1
                    try:
                        neighbor_papers = _fetch_provider_neighbors(
                            provider, provider_identifier, item_direction, limit=int(limit), config=config
                        )
                        stored_count = 0
                        for neighbor in neighbor_papers:
                            if not neighbor.title or neighbor.title == "Untitled":
                                continue
                            existing_id = store.find_existing_paper_id(neighbor)
                            if existing_id == current_id:
                                continue
                            if existing_id is None and len(reserved_ids) >= int(max_nodes):
                                stopped_at_cap = True
                                continue
                            if existing_id is not None and existing_id not in reserved_ids and len(reserved_ids) >= int(max_nodes):
                                stopped_at_cap = True
                                continue
                            # Score new discoveries against the same keyword profile as
                            # normal searches. Existing entries retain their prior score;
                            # revisiting a node must never reset semantic ranking to zero.
                            if existing_id is None:
                                if profile is not None:
                                    candidate_score = rank_papers([neighbor], profile)[0][1]
                                    score_total = candidate_score.total
                                    score_keyword = candidate_score.keyword_score
                                    score_semantic = None
                                    group_hits = candidate_score.group_hits
                                    scoring_version = "citation-keyword-v0.7"
                                else:
                                    score_total = score_keyword = 0.0
                                    score_semantic = None
                                    group_hits = {}
                                    scoring_version = "citation-unscored-v0.7"
                            else:
                                existing_row = store.get(existing_id)
                                if existing_row is None:
                                    score_total = score_keyword = 0.0
                                    score_semantic = None
                                    group_hits = {}
                                    scoring_version = "citation-keyword-v0.7"
                                else:
                                    score_total = float(existing_row["relevance_score"] or 0.0)
                                    score_keyword = float(existing_row["keyword_score"] or 0.0)
                                    score_semantic = existing_row["semantic_score"]
                                    try:
                                        group_hits = json.loads(existing_row["matched_groups_json"] or "{}")
                                    except (json.JSONDecodeError, TypeError):
                                        group_hits = {}
                                    scoring_version = str(existing_row["scoring_version"] or "keyword-v0.1")
                            neighbor_id = store.upsert_paper(
                                neighbor,
                                relevance_score=score_total,
                                matched_groups=group_hits,
                                keyword_score=score_keyword,
                                semantic_score=score_semantic,
                                scoring_version=scoring_version,
                            )
                            if neighbor_id == current_id:
                                continue
                            if neighbor_id not in reserved_ids:
                                if len(reserved_ids) >= int(max_nodes):
                                    stopped_at_cap = True
                                    continue
                                reserved_ids.add(neighbor_id)
                            if item_direction == "references":
                                edge_added = store.record_relation(current_id, neighbor_id, "cites", provider)
                            elif item_direction == "cited-by":
                                edge_added = store.record_relation(neighbor_id, current_id, "cites", provider)
                            else:
                                edge_added = store.record_relation(current_id, neighbor_id, "related", provider)
                            edges_added += int(edge_added)
                            stored_count += 1
                        store.record_citation_fetch(
                            current_id, provider, item_direction, stored_count, requested_limit=int(limit)
                        )
                        _emit(
                            progress,
                            "completed",
                            f"{provider} {item_direction}: received {len(neighbor_papers)}, stored {stored_count}",
                        )
                    except Exception as exc:
                        message = f"{provider} {item_direction} for paper {current_id}: {exc}"
                        errors.append(message)
                        store.record_citation_fetch(
                            current_id, provider, item_direction, 0, message, requested_limit=int(limit)
                        )
                        _emit(progress, "error", message)

                neighbor_ids = _relation_neighbors(store, current_id, item_direction)
                for neighbor_id in neighbor_ids:
                    if neighbor_id == root_id or neighbor_id in depths:
                        if neighbor_id in depths and neighbor_id != root_id:
                            via[neighbor_id].add(item_direction)
                        continue
                    if len(depths) >= int(max_nodes):
                        stopped_at_cap = True
                        break
                    depths[neighbor_id] = current_depth + 1
                    reserved_ids.add(neighbor_id)
                    via[neighbor_id].add(item_direction)
                    next_frontier.append(neighbor_id)
                # Keep processing the remaining requested directions for this
                # frontier node even if its node budget has just been filled;
                # this avoids systematically favoring references over cited-by.
            if len(depths) >= int(max_nodes):
                stopped_at_cap = True
                break
        frontier = list(dict.fromkeys(next_frontier))
        if not frontier or len(depths) >= int(max_nodes):
            break

    papers: list[ExploredPaper] = []
    graph_degrees = store.relation_degrees_within(depths.keys())
    for found_id, found_depth in depths.items():
        if found_id == root_id:
            continue
        row = store.get(found_id)
        if row is None:
            continue
        papers.append(
            ExploredPaper(
                paper_id=found_id,
                depth=found_depth,
                via=sorted(via.get(found_id, set())),
                title=str(row["title"] or "Untitled"),
                year=str(row["published_at"] or "")[:4],
                doi=str(row["doi"] or ""),
                citation_count=int(row["citation_count"] or 0),
                graph_links=graph_degrees.get(found_id, 0),
                url=str(row["url"] or ""),
                relevance_score=float(row["relevance_score"] or 0.0),
                keyword_score=float(row["keyword_score"] or 0.0),
                matched_groups=list(json.loads(row["matched_groups_json"] or "{}")),
            )
        )
    papers.sort(key=lambda item: (item.depth, -item.graph_links, -item.citation_count, item.title.casefold()))
    if stopped_at_cap:
        warnings.append(f"Reached the {max_nodes}-node graph cap; rerun with a larger --max-nodes and --refresh to expand further.")
    if not papers and not errors:
        available = store.identifiers_for_paper(root_id)
        if not (available.get("openalex_id") or available.get("semantic_scholar_id") or available.get("doi") or available.get("arxiv_id")):
            warnings.append("No DOI/OpenAlex/Semantic Scholar/arXiv identifier is available for this seed. Re-ingest it from a provider or add its DOI.")
    return ExploreResult(
        root_id=root_id,
        root_title=str(root["title"]),
        papers=papers,
        edges_added=edges_added,
        provider_requests=requests,
        cache_hits=cache_hits,
        errors=errors,
        warnings=warnings,
        max_nodes=int(max_nodes),
        depth_limit=int(depth),
    )
