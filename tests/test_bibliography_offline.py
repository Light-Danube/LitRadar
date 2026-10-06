from __future__ import annotations

import json
from pathlib import Path

from bibliography import row_to_bibtex
from offline import save_paper_offline
from storage.sqlite import PaperStore
from sources.base import Paper


def _seed(tmp_path: Path, *, pdf_url: str | None = None) -> tuple[PaperStore, int]:
    store = PaperStore(tmp_path / "library.sqlite3")
    paper = Paper(
        source="arxiv",
        title="Adaptive Context for Sarcasm",
        abstract="A useful abstract.",
        authors=["Jane Doe", "John Smith"],
        published_at="2025-01-02",
        url="https://arxiv.org/abs/2501.00001",
        pdf_url=pdf_url,
        venue="arXiv",
        external_id="http://arxiv.org/abs/2501.00001",
        raw={},
    )
    paper_id = store.upsert_paper(
        paper,
        relevance_score=0.91,
        keyword_score=0.80,
        semantic_score=0.97,
        scoring_version="semantic-v0.2",
        matched_groups={"adaptive_context": ["context selection"]},
    )
    return store, paper_id


def test_bibtex_export_contains_core_metadata(tmp_path: Path):
    store, paper_id = _seed(tmp_path)
    try:
        row = store.get(paper_id)
        assert row is not None
        bib = row_to_bibtex(row)
    finally:
        store.close()
    assert bib.startswith("@misc{")
    assert "author = {Jane Doe and John Smith}" in bib
    assert "title = {Adaptive Context for Sarcasm}" in bib
    assert "year = {2025}" in bib
    assert "eprint = {2501.00001}" in bib


def test_offline_bundle_saves_metadata_abstract_and_bib(tmp_path: Path):
    store, paper_id = _seed(tmp_path)
    try:
        row = store.get(paper_id)
        assert row is not None
        result = save_paper_offline(row, tmp_path / "offline")
    finally:
        store.close()
    folder = Path(result["directory"])
    assert (folder / "metadata.json").exists()
    assert (folder / "abstract.txt").read_text(encoding="utf-8") == "A useful abstract."
    assert (folder / "citation.bib").exists()
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["doi"] is None
    assert result["has_pdf"] is False


def test_bibtex_export_avoids_duplicate_keys(tmp_path: Path):
    store, first_id = _seed(tmp_path)
    second = Paper(
        source="arxiv",
        title="Adaptive Context for Emotion",
        abstract="Another abstract.",
        authors=["Jane Doe"],
        published_at="2025-03-04",
        url="https://arxiv.org/abs/2503.00004",
        pdf_url=None,
        venue="arXiv",
        external_id="http://arxiv.org/abs/2503.00004",
        raw={},
    )
    second_id = store.upsert_paper(
        second,
        relevance_score=0.8,
        keyword_score=0.8,
        semantic_score=0.8,
        scoring_version="test",
        matched_groups={},
    )
    try:
        rows = [store.get(first_id), store.get(second_id)]
        from bibliography import export_rows
        output = tmp_path / "library.bib"
        assert export_rows(rows, str(output)) == 2
        text = output.read_text(encoding="utf-8")
    finally:
        store.close()
    assert text.count("@misc{") == 2


def test_offline_existing_pdf_is_preserved(tmp_path: Path):
    store, paper_id = _seed(tmp_path)
    try:
        row = store.get(paper_id)
        assert row is not None
        from offline import offline_pdf_path
        pdf = offline_pdf_path(row, tmp_path / "offline")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-fake")
        result = save_paper_offline(row, tmp_path / "offline")
    finally:
        store.close()
    assert result["has_pdf"] is True
    assert result["downloaded"] is False
    assert pdf.read_bytes() == b"%PDF-fake"
    assert (pdf.parent / "citation.bib").exists()
