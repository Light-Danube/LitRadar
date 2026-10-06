from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_ingest_and_top(tmp_path: Path):
    db = tmp_path / "radar.sqlite3"
    ingest = subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "ingest-fixture", str(ROOT / "data" / "fixture.json")],
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


def test_cli_export_and_download_metadata(tmp_path: Path):
    db = tmp_path / "radar.sqlite3"
    subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--db", str(db), "ingest-fixture", str(ROOT / "data" / "fixture.json"), "--no-semantic"],
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
