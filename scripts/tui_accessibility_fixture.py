"""Disposable EN/UK TUI for manual terminal/screen-reader audits.

All provider, scheduler, download and browser actions are simulated. This is an
audit fixture, not a launch command for the user's real library.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("en", "uk"), default="uk")
    parser.add_argument("--smoke", action="store_true", help="Run a headless fixture check and exit")
    args = parser.parse_args()
    from config import RadarConfig
    from ranking.keywords import KeywordProfile
    from sources.base import Paper
    from textual.widgets import Button, Input, Static
    from ui import LitRadarApp, ScheduleScreen

    with tempfile.TemporaryDirectory(prefix="litbeacon-tui-audit-") as disposable, ExitStack() as mocks:
        root = Path(disposable)
        mocks.enter_context(patch("ui.RadarConfig.load", return_value=RadarConfig(enabled_sources=("synthetic",))))
        mocks.enter_context(patch("ui.KeywordProfile.from_json", return_value=KeywordProfile(groups=[])))
        app = LitRadarApp(root / "synthetic.sqlite3", language=args.language)
        for index, title in enumerate(("Синтетична публікація: довга назва для перевірки читання [literal]", "Synthetic paper: keyboard and terminal review")):
            paper_id = app.store.upsert_paper(Paper(source="synthetic", title=title,
                abstract=("Тестова анотація. Synthetic abstract for scrolling. " * 35),
                published_at=f"202{index}-01-01", doi=f"10.0000/audit-{index}"),
                relevance_score=1.0 - index * 0.2, matched_groups={})
            app.store.set_tags(paper_id, ["синтетичний", "review"])
            app.store.set_status(paper_id, "new" if index == 0 else "read")

        def scheduler(command, **kwargs):
            action = command[3]
            job = command[command.index("--job") + 1]
            # Remove-all deliberately provides a reproducible error state.
            failed = action == "remove" and job == "all"
            return subprocess.CompletedProcess(command, int(failed),
                f"SIMULATED / СИМУЛЯЦІЯ: {action} {job}",
                "Synthetic scheduler failure / Тестова помилка планувальника" if failed else "")

        def search(query, **kwargs):
            kwargs["progress"]("started", "synthetic", "SIMULATED / СИМУЛЯЦІЯ")
            if query.strip().casefold() == "error":
                raise RuntimeError("Synthetic provider failure / Тестова помилка джерела")
            kwargs["progress"]("completed", "synthetic", "SIMULATED / СИМУЛЯЦІЯ")
            return SimpleNamespace(fetched=2, newly_stored=0, library_total=2, source_errors={}), []

        mocks.enter_context(patch("ui.subprocess.run", side_effect=scheduler))
        mocks.enter_context(patch("ui.search_and_ingest", side_effect=search))
        mocks.enter_context(patch("ui.explore_citation_graph", return_value=SimpleNamespace(
            papers=[], edges_added=0, provider_requests=0, cache_hits=0, warnings=[], errors=[])))
        mocks.enter_context(patch("ui.save_paper_offline", return_value={"has_pdf": False}))
        mocks.enter_context(patch("ui.is_available_offline", return_value=False))
        mocks.enter_context(patch("ui.offline_pdf_path", return_value=root / "missing.pdf"))
        mocks.enter_context(patch("ui.webbrowser.open", side_effect=lambda url:
            app.notify("SIMULATED / СИМУЛЯЦІЯ: open URL")))

        async def smoke(pilot):
            await pilot.pause()
            assert len(app.current_rows) == 2
            app.query_one("#source_query", Input).value = "error"
            app.action_search_sources()
            await app.workers.wait_for_complete()
            assert "Synthetic provider failure" in str(app.query_one("#search_status", Static).renderable)
            app.action_manage_jobs()
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert isinstance(app.screen, ScheduleScreen)
            app.screen.query_one("#schedule_remove_all", Button).focus()
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            assert "Synthetic scheduler failure" in str(app.screen.query_one("#schedule_status", Static).renderable)
            await pilot.press("escape")
            await app.action_quit()

        app.run(headless=args.smoke, size=(80, 24) if args.smoke else None,
                auto_pilot=smoke if args.smoke else None)
    print("Disposable TUI audit session finished; actual screen-reader results must be recorded separately.")


if __name__ == "__main__":
    main()
