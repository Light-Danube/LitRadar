from __future__ import annotations

import sys
from pathlib import Path

from notes import NOTE_TEMPLATE, edit_note, export_notes_markdown
from sources.base import Paper
from storage.sqlite import PaperStore


def test_edit_note_uses_structured_template_and_writes_editor_output(tmp_path: Path):
    script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('### Main Hypothesis / Task:\\n\\nTest note\\n', encoding='utf-8')"
    result = edit_note("", editor_command=[sys.executable, "-c", script])
    assert result.startswith("### Main Hypothesis / Task:")
    assert "Test note" in result
    assert "### Proposed Method & Model:" in NOTE_TEMPLATE


def test_export_notes_markdown_contains_metadata_abstract_and_notes(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(
                source="semantic_scholar",
                title="Task-Dependent Context Selection",
                abstract="An abstract for a relevant paper.",
                authors=["Jane Doe", "John Smith"],
                published_at="2025-04-12",
                doi="10.1000/example",
                url="https://example.org/paper",
                venue="Example Conference",
            ),
            relevance_score=0.9,
            matched_groups={"context": ["context selection"]},
        )
        store.set_notes(paper_id, "Compare the baseline and selection strategy.")
        output = tmp_path / "notes.md"
        rows = store.list_papers(status="all")
        assert export_notes_markdown(rows, output) == 1
        content = output.read_text(encoding="utf-8")
        assert "# LitBeacon — Literature Notes" in content
        assert "Task-Dependent Context Selection" in content
        assert "Jane Doe, John Smith" in content
        assert "10.1000/example" in content
        assert "An abstract for a relevant paper." in content
        assert "Compare the baseline" in content
    finally:
        store.close()
