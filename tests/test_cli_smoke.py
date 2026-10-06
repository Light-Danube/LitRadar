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
