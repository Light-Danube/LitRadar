"""Bounded, local annotation adapters. No provider/model network calls."""
import hashlib
import json

from storage.sqlite import PaperStore


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _decoded(value, default):
    try:
        return json.loads(value or "")
    except (ValueError, TypeError):
        return default


def record_batch(store: PaperStore, paper_id: int, entries: list[dict], method: str) -> dict:
    if store.get(paper_id) is None:
        raise KeyError(paper_id)
    if len(entries) > 100 or len(_json(entries).encode("utf-8")) > 1_000_000:
        raise ValueError("Annotation batch is too large")
    existing = {row[0] for row in store.conn.execute(
        "SELECT id FROM paper_annotations WHERE paper_id=?", (paper_id,)
    )}
    items = []
    with store.conn:
        for entry in entries:
            key = hashlib.sha256(_json([method, entry]).encode("utf-8")).hexdigest()
            items.append(dict(store.add_annotation(paper_id, **entry, origin_method=method,
                                                   evidence_key=key, commit=False)))
    return {"items": items, "added": len({item["id"] for item in items} - existing)}


def import_annotations(store: PaperStore, paper_id: int, entries: list[dict], filename: str) -> dict:
    # Uploaded labels/timestamps cannot impersonate extraction or generation.
    imported = [{"kind": "imported", "content": item["content"],
                 "source_ref": f"{filename}: {item.get('source_ref') or ''}".rstrip(": ")}
                for item in entries]
    return record_batch(store, paper_id, imported, "json_import")


def extract_annotations(store: PaperStore, paper_id: int, *, include_generated: bool = False,
                        language: str = "en") -> dict:
    row = store.get(paper_id)
    if row is None:
        raise KeyError(paper_id)
    snapshot = {"title": row["title"], "abstract_excerpt": (row["abstract"] or "")[:10000],
                "venue": row["venue"], "published_at": row["published_at"],
                "authors": _decoded(row["authors_json"], [])[:20],
                "source_tags": _decoded(row["source_tags_json"], [])[:30],
                "citation_count": row["citation_count"]}
    source = f"SQLite paper #{paper_id}; {row['source']}; DOI {row['doi'] or 'n/a'}"[:2000]
    # A failed suggestion must not leave a partially committed extraction action.
    entries = [("metadata_extraction", {"kind": "extracted", "content": _json(snapshot), "source_ref": source})]
    if include_generated:
        assessment = _decoded(row["llm_assessment_json"], {})
        if isinstance(assessment, dict) and assessment.get("summary"):
            content = _json({k: assessment[k] for k in ("summary", "fit_reason", "suggested_tags") if k in assessment})
            method = "stored_assessment"
            source = f"Stored assessment: {assessment.get('provider', 'unknown')} / {assessment.get('model', 'unknown')}"[:2000]
        else:
            content = ("Перевірте метод, базові порівняння та обмеження в повному тексті. "
                       "Які дані підтверджують висновки? " if language == "uk" else
                       "Check the method, baselines and limitations in the full text. "
                       "What evidence supports the conclusions? ") + row["title"][:1000]
            method = "local_heuristic"
            source = f"Local reading-prompt template v1; paper #{paper_id}; language={language}"
        entries.append((method, {"kind": "generated", "content": content, "source_ref": source}))
    existing = {row[0] for row in store.conn.execute("SELECT id FROM paper_annotations WHERE paper_id=?", (paper_id,))}
    items = []
    with store.conn:
        for method, entry in entries:
            key = hashlib.sha256(_json([method, entry]).encode("utf-8")).hexdigest()
            items.append(dict(store.add_annotation(paper_id, **entry, origin_method=method,
                                                   evidence_key=key, commit=False)))
    result = {"items": items, "added": len({item["id"] for item in items} - existing)}
    return result
