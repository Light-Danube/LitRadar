from pathlib import Path
import json
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def paper_fixture(tmp_path: Path) -> Path:
    # The Docker build deliberately excludes data/. Keep CLI test inputs
    # disposable and independent of the user's library and optional models.
    fixture = tmp_path / "papers.json"
    fixture.write_text(json.dumps([
        {"source": "fixture", "title": "Adaptive Context Selection for Sarcasm and Emotion",
         "abstract": "Context selection for sarcasm detection in online conversations."},
        {"source": "fixture", "title": "Context Retrieval for Language Models"},
        {"source": "fixture", "title": "Synthetic Image Classification"},
    ]), encoding="utf-8")
    return fixture


def test_fixture_ingest_and_top(tmp_path: Path, paper_fixture: Path):
    db = tmp_path / "radar.sqlite3"
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "ingest-fixture", str(paper_fixture), "--no-semantic"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Ingested 3 fixture papers" in ingest.stdout

    top = subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "top", "2"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Adaptive Context Selection" in top.stdout


def test_cli_export_and_download_metadata(tmp_path: Path, paper_fixture: Path):
    db = tmp_path / "radar.sqlite3"
    subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "ingest-fixture", str(paper_fixture), "--no-semantic"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    bib = tmp_path / "read.bib"
    subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "export-bibtex", "--status", "all", "--output", str(bib)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert bib.exists()
    assert "@" in bib.read_text(encoding="utf-8")

    offline_dir = tmp_path / "offline"
    subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "download", "1", "--output-dir", str(offline_dir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert list(offline_dir.glob("1-*/metadata.json"))
    assert list(offline_dir.glob("1-*/abstract.txt"))
    assert list(offline_dir.glob("1-*/citation.bib"))
