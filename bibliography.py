from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def _escape(value: str) -> str:
    value = (value or "").replace("\\", r"\\").replace("{", r"\\{").replace("}", r"\\}")
    return value.replace("\n", " ").strip()


def _cite_key(row) -> str:
    authors = []
    try:
        import json
        authors = json.loads(row["authors_json"] or "[]")
    except Exception:
        authors = []
    surname = "paper"
    if authors:
        first_author = str(authors[0]).strip()
        # Support both "Jane Doe" and bibliographic "Doe, Jane" forms.
        surname_raw = first_author.split(",", 1)[0] if "," in first_author else first_author.split()[-1]
        ascii_surname = unicodedata.normalize("NFKD", surname_raw).encode("ascii", "ignore").decode("ascii")
        surname = re.sub(r"[^A-Za-z0-9]+", "", ascii_surname).lower() or "paper"
    year = (row["published_at"] or "")[:4] or "nodate"
    words = re.findall(r"[A-Za-z0-9]+", unicodedata.normalize("NFKD", row["title"]))
    token = next((w.lower() for w in words if len(w) > 3), "paper")
    return f"{surname}{year}{token}"


def _entry_type(row) -> str:
    source = row["source"]
    if source == "arxiv":
        return "misc"
    raw = {}
    try:
        import json
        raw = json.loads(row["raw_json"] or "{}")
    except Exception:
        raw = {}
    raw_type = str(raw.get("type") or "").lower()
    if raw_type in {"proceedings-article", "conference-paper"}:
        return "inproceedings"
    return "article"


def row_to_bibtex(row, *, cite_key: str | None = None) -> str:
    entry_type = _entry_type(row)
    key = cite_key or _cite_key(row)
    authors = []
    try:
        import json
        authors = json.loads(row["authors_json"] or "[]")
    except Exception:
        authors = []

    lines = [f"@{entry_type}{{{key},"]
    if authors:
        lines.append(f"  author = {{{_escape(' and '.join(authors))}}},")
    lines.append(f"  title = {{{_escape(row['title'])}}},")
    year = (row["published_at"] or "")[:4]
    if year.isdigit():
        lines.append(f"  year = {{{year}}},")
    venue = (row["venue"] or "").strip()
    if venue:
        field = "booktitle" if entry_type == "inproceedings" else "journal"
        lines.append(f"  {field} = {{{_escape(venue)}}},")
    if row["doi"]:
        lines.append(f"  doi = {{{_escape(row['doi'])}}},")
    if row["url"]:
        lines.append(f"  url = {{{_escape(row['url'])}}},")
    elif row["pdf_url"]:
        lines.append(f"  url = {{{_escape(row['pdf_url'])}}},")
    if row["source"] == "arxiv" and row["external_id"]:
        arxiv_id = str(row["external_id"]).rstrip("/").split("/")[-1]
        if arxiv_id:
            lines.append(f"  eprint = {{{_escape(arxiv_id)}}},")
            lines.append("  archivePrefix = {arXiv},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def export_rows(rows: Iterable, output_path: str) -> int:
    entries = []
    used: dict[str, int] = {}
    for row in rows:
        base_key = _cite_key(row)
        occurrence = used.get(base_key, 0) + 1
        used[base_key] = occurrence
        key = base_key if occurrence == 1 else f"{base_key}{occurrence}"
        entries.append(row_to_bibtex(row, cite_key=key))
    text = "\n\n".join(entries)
    if text:
        text += "\n"
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return len(entries)
