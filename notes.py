from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

NOTE_TEMPLATE = """### Main Hypothesis / Task:


### Proposed Method & Model:


### Datasets & Baselines:


### Key Weakness / Limitation:


### Relevance to my dissertation:


"""


def note_editor_command() -> list[str] | None:
    """Return a usable editor command or None when no editor is configured."""
    configured = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if configured:
        return shlex.split(configured, posix=(os.name != "nt"))
    if os.name == "nt":
        return ["notepad.exe"]
    # Avoid guessing a full-screen editor in a non-interactive environment.
    return None


def edit_note(initial: str = "", *, editor_command: list[str] | None = None) -> str:
    command = editor_command if editor_command is not None else note_editor_command()
    if not command:
        raise RuntimeError("No editor configured. Set EDITOR/VISUAL or pass note text directly.")
    content = initial if initial.strip() else NOTE_TEMPLATE
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md", prefix="litradar-note-", delete=False
        ) as handle:
            handle.write(content)
            path = Path(handle.name)
        subprocess.run([*command, str(path)], check=True)
        return path.read_text(encoding="utf-8")
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def export_notes_markdown(rows: Iterable, output_path: str | Path) -> int:
    """Export paper metadata, abstract, and user notes as a readable Markdown file."""
    sections = ["# LitBeacon — Literature Notes", ""]
    count = 0
    for row in rows:
        count += 1
        title = str(row["title"] or "Untitled").strip()
        authors = []
        try:
            import json
            authors = json.loads(row["authors_json"] or "[]")
        except (ValueError, TypeError):
            pass
        doi = str(row["doi"] or "").strip()
        url = str(row["url"] or "").strip()
        published = str(row["published_at"] or "n.d.")[:10]
        venue = str(row["venue"] or "").strip()
        link = f"https://doi.org/{doi}" if doi else url
        sections.append(f"## {title}")
        sections.append("")
        sections.append(f"- **Authors:** {', '.join(authors) if authors else 'Unknown'}")
        sections.append(f"- **Year/date:** {published}")
        if venue:
            sections.append(f"- **Venue:** {venue}")
        if doi:
            sections.append(f"- **DOI:** {doi}")
        if link:
            sections.append(f"- **URL:** {link}")
        sections.extend(["", "### Abstract", "", str(row["abstract"] or "(No abstract available.)").strip(), "", "### Research notes", "", str(row["notes"] or "(No notes yet.)").strip(), "", "---", ""])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections), encoding="utf-8")
    return count
