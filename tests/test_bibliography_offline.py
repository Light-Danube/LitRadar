from __future__ import annotations

import json
from pathlib import Path

from bibliography import row_to_bibtex
from offline import save_paper_offline
from storage.sqlite import PaperStore
from sources.base import Paper


def _seed(tmp_path: Path, *, pdf_url: str | None = None, doi: str | None = None) -> tuple[PaperStore, int]:
    store = PaperStore(tmp_path / "library.sqlite3")
    paper = Paper(
        source="arxiv",
        title="Adaptive Context for Sarcasm",
        abstract="A useful abstract.",
        authors=["Jane Doe", "John Smith"],
        published_at="2025-01-02",
        url="https://arxiv.org/abs/2501.00001",
        pdf_url=pdf_url,
        doi=doi,
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


def test_download_rejects_html_disguised_as_pdf(tmp_path: Path):
    html = tmp_path / "not-a-pdf.html"
    html.write_text("<html>403 Forbidden</html>", encoding="utf-8")
    store, paper_id = _seed(tmp_path, pdf_url=html.as_uri())
    try:
        row = store.get(paper_id)
        result = save_paper_offline(row, tmp_path / "offline")
    finally:
        store.close()
    assert result["has_pdf"] is False
    folder = Path(result["directory"])
    assert "not a PDF" in (folder / "download_error.txt").read_text(encoding="utf-8")
    assert not list(folder.glob("*.part"))


def test_readable_pdf_filename_includes_year_author_and_title(tmp_path: Path):
    from offline import offline_pdf_path

    store, paper_id = _seed(tmp_path)
    try:
        row = store.get(paper_id)
        path = offline_pdf_path(row, tmp_path / "offline")
    finally:
        store.close()
    assert path.name.startswith("2025_Doe_Adaptive-Context-for-Sarcasm")
    assert path.suffix == ".pdf"


def test_unpaywall_fallback_is_used_after_invalid_direct_pdf(tmp_path: Path, monkeypatch):
    import offline

    html = tmp_path / "blocked.html"
    html.write_text("<html>captcha</html>", encoding="utf-8")
    legal_pdf = tmp_path / "open-access.pdf"
    legal_pdf.write_bytes(b"%PDF-test content")
    monkeypatch.setattr(offline, "resolve_unpaywall_pdf_urls", lambda doi, email: [legal_pdf.as_uri()])
    store, paper_id = _seed(tmp_path, pdf_url=html.as_uri(), doi="10.1000/example")
    try:
        row = store.get(paper_id)
        result = save_paper_offline(row, tmp_path / "offline", unpaywall_email="researcher@example.org")
    finally:
        store.close()
    assert result["has_pdf"] is True
    assert result["downloaded"] is True
    assert result["pdf_path"].read_bytes().startswith(b"%PDF-")
    import json
    metadata = json.loads((Path(result["directory"]) / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["pdf_retrieval"] == "unpaywall"


def test_successful_pdf_download_clears_stale_retrieval_errors(tmp_path: Path):
    import json
    from offline import paper_dir

    pdf = tmp_path / "valid.pdf"
    pdf.write_bytes(b"%PDF-valid bytes")
    store, paper_id = _seed(tmp_path, pdf_url=pdf.as_uri())
    try:
        row = store.get(paper_id)
        folder = paper_dir(row, tmp_path / "offline")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "download_error.txt").write_text("Old transient failure", encoding="utf-8")
        (folder / "retrieval_status.txt").write_text("Old unavailable status", encoding="utf-8")
        result = save_paper_offline(row, tmp_path / "offline")
    finally:
        store.close()
    assert result["has_pdf"] is True
    assert not (folder / "download_error.txt").exists()
    assert not (folder / "retrieval_status.txt").exists()
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["saved_from_litradar"] == "0.6.0"


def test_bibtex_citekey_is_lowercase_and_handles_surname_comma_form(tmp_path: Path):
    from bibliography import row_to_bibtex

    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(
                source="semantic_scholar",
                title="Attention Is All You Need",
                authors=["Vaswani, Ashish"],
                published_at="2017-06-12",
                venue="NeurIPS",
            ),
            relevance_score=0.9,
            matched_groups={},
        )
        row = store.get(paper_id)
        bib = row_to_bibtex(row)
    finally:
        store.close()
    assert "@article{vaswani2017attention," in bib
