from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import webbrowser
from pathlib import Path

from litradar_runtime import DEFAULT_DB, DEFAULT_PROFILE, DEFAULT_SCAN_CONFIG, WORKSPACE_ROOT, ensure_user_defaults
from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.personalization import build_model, explain_candidate, neutral_results, score_rows
from storage.sqlite import PaperStore, SORT_CHOICES, STATUSES
from offline import is_available_offline, offline_pdf_path, save_paper_offline
from pipeline import search_and_ingest
from citation_intelligence import explore_citation_graph

from ui_locales import HELP_TEXT, localize_explanation, normalize_language, tr

from rich.text import Text
from textual.app import App, ComposeResult
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.worker import get_current_worker
from textual.widgets import Button, DataTable, Footer, Header, Input, ProgressBar, Select, Static


SORT_LABELS = {
    "relevance_score": "Relevance",
    "recent": "Published ↓",
    "published_oldest": "Published ↑",
    "newest_added": "Added ↓",
    "title": "Title A–Z",
    "score": "Score ↓",
    "citations": "Citations ↓",
    "references": "References ↓",
    "influential_citations": "Influential citations ↓",
    "personalized": "Personalized",
}


def highlight_search_terms(body: str, abstract: str, query: str) -> Text:
    """Return safe Rich text with matching query tokens highlighted in the abstract."""
    rendered = Text(body)
    if not query or not abstract:
        return rendered
    abstract_start = body.rfind(abstract)
    if abstract_start < 0:
        return rendered
    tokens = list(dict.fromkeys(re.findall(r"[\w-]+", query, flags=re.UNICODE)))
    for token in tokens:
        for match in re.finditer(re.escape(token), abstract, flags=re.IGNORECASE):
            rendered.stylize("bold yellow", abstract_start + match.start(), abstract_start + match.end())
    return rendered


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close", show=False), Binding("q", "close", "Close", show=False)]

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self.language = normalize_language(language)

    def _t(self, key: str, **kwargs) -> str:
        return tr(self.language, key, **kwargs)

    def compose(self) -> ComposeResult:
        with Vertical(id="help_dialog"):
            with VerticalScroll(id="help_scroll", can_focus=True):
                yield Static(self._t(HELP_TEXT), id="help_body")
            yield Button(self._t("Close"), id="help_close")

    def on_mount(self) -> None:
        self.query_one("#help_scroll", VerticalScroll).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help_close":
            self.dismiss()

    def action_close(self) -> None:
        self.dismiss()


class TagScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, store: PaperStore, paper_id: int, language: str = "en") -> None:
        super().__init__()
        self.store = store
        self.paper_id = paper_id
        self.language = normalize_language(language)

    def _t(self, key: str, **kwargs) -> str:
        return tr(self.language, key, **kwargs)

    def compose(self) -> ComposeResult:
        row = self.store.get(self.paper_id)
        current = ", ".join(json.loads(row["tags_json"] or "[]")) if row else ""
        existing = ", ".join(self.store.all_tags()) or self._t("(none yet)")
        with Vertical(id="tag_dialog"):
            yield Static(self._t("[b]Edit tags[/b]"), id="tag_title")
            yield Static(self._t("Existing tags: {existing}", existing=existing), id="tag_existing", markup=False)
            yield Input(value=current, placeholder=self._t("tag-one, tag-two, …"), id="tag_input")
            yield Static("", id="tag_error", markup=False)
            with Horizontal(id="tag_buttons"):
                yield Button(self._t("Save"), id="tag_save", variant="primary")
                yield Button(self._t("Cancel"), id="tag_cancel")

    def on_mount(self) -> None:
        self.query_one("#tag_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tag_save":
            event.stop()
            self._save_tags(self.query_one("#tag_input", Input).value)
        elif event.button.id == "tag_cancel":
            event.stop()
            self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tag_input":
            event.stop()
            self._save_tags(event.value)

    def _save_tags(self, raw: str) -> None:
        tags = [part.strip() for part in raw.split(",") if part.strip()]
        try:
            self.store.set_tags(self.paper_id, tags)
        except (sqlite3.Error, OSError, KeyError):
            # A failed commit must not leave a pending edit for a later action.
            try:
                self.store.conn.rollback()
            except sqlite3.Error:
                pass
            self.query_one("#tag_error", Static).update(
                self._t("Could not save tags. Your draft is retained; retry or cancel."))
            self.query_one("#tag_input", Input).focus()
            return
        self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class ScheduleScreen(ModalScreen[None]):
    """Small OS-scheduler manager: install or remove scan/digest jobs deliberately."""

    BINDINGS = [Binding("escape", "close", "Close", show=False), Binding("q", "close", "Close", show=False)]

    def __init__(self, config_path: str | Path | None = None, language: str = "en", *,
                 db_path: str | Path = DEFAULT_DB, profile_path: str | Path = DEFAULT_PROFILE) -> None:
        ensure_user_defaults()
        super().__init__()
        self.language = normalize_language(language)
        self._busy = False
        self.config_path = Path(config_path or DEFAULT_SCAN_CONFIG)
        self.db_path = Path(db_path)
        self.profile_path = Path(profile_path)

    def _t(self, key: str, **kwargs) -> str:
        return tr(self.language, key, **kwargs)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="schedule_dialog", can_focus=True):
            yield Static(self._t("Scheduled jobs"), id="schedule_title", markup=False)
            yield Static(
                self._t("Scan fills the local library. Digest sends the configured daily/weekly report.\n"
                "Remove only the job you do not want; removing a job does not delete papers or settings.\n"
                "The built-in manager supports Windows Task Scheduler. On Linux/macOS, remove disables LitBeacon's scheduled-run config; remove the matching cron/launchd entry too."),
                id="schedule_help",
                markup=False,
            )
            with VerticalScroll(id="schedule_status_scroll", can_focus=True):
                yield Static(self._t("Checking scheduler status…"), id="schedule_status", markup=False)
            with Horizontal(id="schedule_action_row"):
                yield Button(self._t("Refresh status"), id="schedule_status_btn")
                yield Button(self._t("Install scan · daily 07:30"), id="schedule_install_scan")
                yield Button(self._t("Install digest · weekly 09:00"), id="schedule_install_digest")
            with Horizontal(id="schedule_remove_row"):
                yield Button(self._t("Remove scan"), id="schedule_remove_scan", variant="warning")
                yield Button(self._t("Remove digest"), id="schedule_remove_digest", variant="warning")
                yield Button(self._t("Remove all"), id="schedule_remove_all", variant="error")
                yield Button(self._t("Close"), id="schedule_close")

    def on_mount(self) -> None:
        self.query_one("#schedule_close", Button).focus()
        self._start_schedule("status", "all")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        actions = {
            "schedule_status_btn": ("status", "all", "daily", "08:00"),
            "schedule_install_scan": ("install", "scan", "daily", "07:30"),
            "schedule_install_digest": ("install", "digest", "weekly", "09:00"),
            "schedule_remove_scan": ("remove", "scan", "daily", "08:00"),
            "schedule_remove_digest": ("remove", "digest", "daily", "08:00"),
            "schedule_remove_all": ("remove", "all", "daily", "08:00"),
        }
        if event.button.id == "schedule_close":
            self.dismiss()
            return
        values = actions.get(event.button.id)
        if values:
            self._start_schedule(*values)

    def _start_schedule(self, action: str, job: str, frequency: str = "daily", when: str = "08:00") -> None:
        if self._busy:
            return
        self._busy = True
        self.query_one("#schedule_status", Static).update(self._t("Running scheduler command…"))
        for button in self.query(Button):
            if button.id != "schedule_close":
                button.disabled = True
        self._run_schedule(action, job, frequency, when)

    @work(exclusive=True, thread=True)
    def _run_schedule(self, action: str, job: str, frequency: str = "daily", when: str = "08:00") -> None:
        worker = get_current_worker()
        app = self.app
        command = [
            sys.executable, str(Path(__file__).resolve().parent / "cli.py"),
            "--db", str(self.db_path.resolve()), "schedule", action,
            "--job", job, "--frequency", frequency, "--time", when,
            "--config", str(self.config_path.resolve()), "--profile", str(self.profile_path.resolve()),
        ]
        try:
            completed = subprocess.run(command, cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=60, check=False)
            message = (completed.stdout or "").strip()
            if completed.stderr:
                message = (message + "\n" + completed.stderr.strip()).strip()
            if not message:
                message = self._t("Schedule command finished with exit code {code}.", code=completed.returncode)
            if completed.returncode:
                message = self._t("Command exit code {code}.\n{message}", code=completed.returncode, message=message)
        except (OSError, subprocess.TimeoutExpired) as exc:
            message = self._t("Could not run scheduler command: {error}: {message}", error=type(exc).__name__, message=exc)
        # Screen has no call_from_thread; only App owns the UI event loop.
        # A closed dialog must not receive a late subprocess result.
        if not worker.is_cancelled and app.is_running:
            app.call_from_thread(self._display_status, message)

    def _display_status(self, message: str) -> None:
        if not self.is_mounted:
            return
        self._busy = False
        for button in self.query(Button):
            button.disabled = False
        self.query_one("#schedule_status", Static).update(message)

    def action_close(self) -> None:
        self.dismiss()




class LitRadarApp(App[None]):
    """Interactive research inbox for LitBeacon (formerly LitRadar)."""

    TITLE = "LitBeacon"
    SUB_TITLE = "Research Workspace · formerly LitRadar"
    CSS_PATH = "ui.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
        Binding("r", "mark_read", "Read"),
        Binding("t", "to_read", "To Read"),
        Binding("d", "dismiss", "Dismiss"),
        Binding("u", "restore", "Restore"),
        Binding("y", "positive_feedback", "Useful"),
        Binding("n", "negative_feedback", "Not relevant"),
        Binding("g", "tags", "Tags"),
        Binding("l", "download_offline", "Offline"),
        Binding("o", "open", "Open"),
        Binding("i", "open_doi", "DOI"),
        Binding("/", "focus_search", "Search"),
        Binding("f", "focus_status", "Filter"),
        Binding("s", "focus_sort", "Sort"),
        Binding("k", "focus_tag", "Tag"),
        Binding("ctrl+enter", "search_sources", "Fetch papers"),
        Binding("c", "explore_citations", "Citation graph"),
        Binding("j", "manage_jobs", "Scheduled jobs"),
    ]

    def __init__(self, db_path: str | Path, language: str | None = None) -> None:
        ensure_user_defaults()
        super().__init__()
        self.language = normalize_language(language or os.environ.get("LITBEACON_TUI_LANGUAGE", os.environ.get("LITRADAR_TUI_LANGUAGE", "en")))
        self.sub_title = self._t(self.SUB_TITLE)
        self._localize_bindings()
        self.db_path = str(db_path)
        self.store = PaperStore(db_path)
        self.current_rows = []
        self.current_display_scores: dict[int, float] = {}
        self.profile = KeywordProfile.from_json(DEFAULT_PROFILE)
        self._personal_model = None
        self._personalization_model_active = False
        self._search_query = ""
        self._search_source_count = 0
        self._search_source_done: set[str] = set()
        self._search_source_messages: dict[str, str] = {}
        self._search_phase_line = self._t("Ready. Enter a query above; provider activity and the final summary will appear here.")
        self._citation_busy = False

    def _main_query(self, selector, expect_type=None):
        """Keep app callbacks on the library screen while a modal is active."""
        return self.screen_stack[0].query_one(selector, expect_type)

    def _t(self, key: str, **kwargs) -> str:
        return tr(self.language, key, **kwargs)

    def _status_label(self, status: str) -> str:
        if self.language == "en":
            return status.replace("-", " ").title()
        return self._t(status)

    def _localize_bindings(self) -> None:
        translated = type(self._bindings)([
            Binding(binding.key, binding.action, self._t(binding.description),
                    show=binding.show, priority=binding.priority)
            for binding in self.BINDINGS
        ])
        # Constructing a binding map normalizes punctuation keys, unlike bind().
        # Retain framework bindings such as Ctrl+Q and the command palette.
        keys = translated.key_to_bindings
        for key, bindings in self._bindings.key_to_bindings.items():
            if key not in keys:
                keys[key] = bindings
        self._bindings = translated

    def _localize_controls(self) -> None:
        for selector, label in (
            ("#search", "Saved library"), ("#status", "Status"),
            ("#sort", "Sort"), ("#tag", "Tags"),
            ("#source_query", "Online search"), ("#language", "Language"),
        ):
            widget = self._main_query(selector)
            widget.border_title = self._t(label)
            widget.tooltip = self._t(label)

    def set_language(self, language: str) -> None:
        language = normalize_language(language)
        if language == self.language:
            return
        selected_id = self._selected_id()
        self.language = language
        self.sub_title = self._t(self.SUB_TITLE)
        self._localize_bindings()
        self._main_query("#search", Input).placeholder = self._t("Filter saved library by title/abstract/notes…")
        self._main_query("#source_query", Input).placeholder = self._t("Search online sources…")
        self._main_query("#search_sources", Button).label = self._t("Fetch papers")
        for selector, options in (
            ("#status", [(self._status_label(value), value) for value in ["all", *STATUSES]]),
            ("#sort", [(self._t(label), value) for value, label in SORT_LABELS.items()]),
        ):
            widget = self._main_query(selector, Select)
            value = widget.value
            widget.set_options(options)
            widget.value = value
        self._refresh_tag_options()
        table = self._main_query("#papers", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", self._t("Score"), self._t("Status"), self._t("Year"), self._t("Title"))
        if not self._search_query:
            self._search_phase_line = self._t("Ready. Enter a query above; provider activity and the final summary will appear here.")
            self._main_query("#search_status", Static).update(self._search_phase_line)
        else:
            self._render_search_activity()
        self.refresh_rows()
        if selected_id is not None:
            for index, row in enumerate(self.current_rows):
                if int(row["id"]) == selected_id:
                    table.move_cursor(row=index)
                    break
            self._show_details()
        self._localize_controls()
        self.refresh_bindings()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="toolbar"):
            yield Input(placeholder=self._t("Filter saved library by title/abstract/notes…"), id="search")
            yield Select(
                [(self._status_label(label), label) for label in ["all", *STATUSES]],
                value="all",
                id="status",
                allow_blank=False,
            )
            yield Select(
                [(self._t(label), key) for key, label in SORT_LABELS.items()],
                value="relevance_score",
                id="sort",
                allow_blank=False,
            )
            yield Select([(self._t("All tags"), "__all_tags__")], value="__all_tags__", id="tag", allow_blank=False)
            yield Static(self._t("Papers: 0"), id="library_count")
        with Horizontal(id="actionbar"):
            yield Input(placeholder=self._t("Search online sources…"), id="source_query")
            yield Button(self._t("Fetch papers"), id="search_sources", variant="primary")
            yield Select([("English", "en"), ("Українська", "uk")], value=self.language, id="language", allow_blank=False)
        with Horizontal(id="search_progress_row"):
            yield ProgressBar(total=100, show_eta=False, show_percentage=True, id="search_progress")
            yield Static(
                self._t("Ready. Enter a query above; provider activity and the final summary will appear here."),
                id="search_status",
                markup=False,
            )
        with Horizontal(id="main"):
            yield DataTable(id="papers", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(id="details", can_focus=True):
                yield Static(self._t("Select a paper"), id="details_title", markup=False)
                yield Static("", id="details_body")
        yield Footer()

    def on_mount(self) -> None:
        self._update_compact_layout()
        self._localize_controls()
        table = self._main_query("#papers", DataTable)
        table.add_columns("ID", self._t("Score"), self._t("Status"), self._t("Year"), self._t("Title"))
        self._refresh_tag_options()
        self.refresh_rows()

    def on_resize(self) -> None:
        self._update_compact_layout()

    def _update_compact_layout(self) -> None:
        if self.screen_stack:
            self.screen_stack[0].set_class(self.size.width < 110, "compact")

    def on_unmount(self) -> None:
        self.store.close()

    def _selected_id(self) -> int | None:
        table = self._main_query("#papers", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.current_rows):
            return None
        return int(self.current_rows[table.cursor_row]["id"])

    def refresh_rows(self) -> None:
        query = self._main_query("#search", Input).value.strip() or None
        status = str(self._main_query("#status", Select).value or "all")
        sort = str(self._main_query("#sort", Select).value or "relevance_score")
        tag_value = str(self._main_query("#tag", Select).value or "__all_tags__")
        tag = None if tag_value == "__all_tags__" else tag_value
        library_total = self.store.total_count()
        view_total = self.store.total_count(status=status, query=query, tag=tag)
        self._main_query("#library_count", Static).update(self._t("Library: {total} | View: {view}", total=library_total, view=view_total))

        if sort == "personalized":
            config = RadarConfig.load()
            scan_limit = config.personalization_scan_limit
            base_rows = self.store.list_papers(
                limit=scan_limit, status=status, query=query, tag=tag, sort="relevance_score"
            )
            if not config.personalization_enabled:
                model = None
                self._personalization_model_active = False
                ranked = neutral_results(base_rows)
            else:
                self._personalization_model_active = True
                if self._personal_model is None:
                    self._personal_model = build_model(
                        self.store.feedback_rows(), min_feedback=config.personalization_min_feedback
                    )
                model = self._personal_model
                ranked = score_rows(base_rows, model, self._profile(), weight=config.personalized_weight)
            self.current_rows = [row for row, _result in ranked[:200]]
            self.current_display_scores = {int(row["id"]): result.score for row, result in ranked[:200]}
        else:
            self.current_rows = self.store.list_papers(
                limit=200, status=status, query=query, tag=tag, sort=sort
            )
            self.current_display_scores = {int(row["id"]): float(row["relevance_score"] or 0.0) for row in self.current_rows}

        table = self._main_query("#papers", DataTable)
        table.clear(columns=False)
        for row in self.current_rows:
            year = (row["published_at"] or "")[:4] or "—"
            display_score = self.current_display_scores.get(int(row["id"]), float(row["relevance_score"] or 0.0))
            table.add_row(str(row["id"]), f"{display_score:.3f}", self._status_label(row["status"]), year, Text(row["title"]))
        self._show_details()

    def _profile(self) -> object:
        return self.profile

    def _show_details(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            self._main_query("#details_title", Static).update(self._t("No paper selected"))
            self._main_query("#details_body", Static).update("")
            return
        row = self.store.get(paper_id)
        if row is None:
            return
        tags = ", ".join(json.loads(row["tags_json"] or "[]")) or "—"
        source_tags = ", ".join(json.loads(row["source_tags_json"] or "[]")) or "—"
        abstract_value = row["abstract"] or self._t("(no abstract)")
        body = (
            f"{self._t('Status')}: {self._status_label(row['status'])}\n"
            f"{self._t('Base score')}: {row['relevance_score']:.3f}\n"
            f"{self._t('Displayed score')}: {self.current_display_scores.get(int(row['id']), float(row['relevance_score'] or 0.0)):.3f}\n"
            f"{self._t('Source')}: {row['source']}\n"
            f"{self._t('Published')}: {row['published_at'] or self._t('n/a')}\n"
            f"{self._t('Venue')}: {row['venue'] or self._t('n/a')}\n"
            f"DOI: {row['doi'] or self._t('n/a')}\n"
            f"{self._t('Citations')}: {row['citation_count']}\n"
            f"{self._t('References')}: {row['reference_count'] if row['reference_count'] is not None else self._t('n/a')}\n"
            f"{self._t('Influential citations')}: {row['influential_citation_count'] if row['influential_citation_count'] is not None else self._t('n/a')}\n"
            f"{self._t('Tags')}: {tags}\n"
            f"{self._t('Source tags')}: {source_tags}\n"
            f"{self._t('Offline PDF')}: {offline_pdf_path(row) if is_available_offline(row) else self._t('not saved')}\n\n"
            f"{abstract_value}"
        )
        if str(self._main_query("#sort", Select).value) == "personalized" and self._personalization_model_active and self._personal_model is not None:
            config = RadarConfig.load()
            explanation = explain_candidate(
                row,
                self._personal_model,
                self._profile(),
                weight=config.personalized_weight,
            )
            if self.language == "uk":
                explanation = localize_explanation(explanation)
            body += f"\n\n{self._t('Personalized recommendation')}: {explanation}"
        elif str(self._main_query("#sort", Select).value) == "personalized":
            body += "\n\n" + self._t("Personalized recommendation: not active yet; add more feedback or enable personalization.")
        self._main_query("#details_title", Static).update(row["title"])
        search_query = self._main_query("#search", Input).value.strip()
        # Construct Rich Text from literal content so abstracts containing
        # markup-like characters remain safe to display.
        self._main_query("#details_body", Static).update(
            highlight_search_terms(body, abstract_value, search_query)
        )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_details()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self.refresh_rows()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_sources":
            self.action_search_sources()

    def action_search_sources(self) -> None:
        if self._citation_busy:
            self.notify(self._t("Citation exploration is still running."), severity="warning")
            return
        query = self._main_query("#source_query", Input).value.strip()
        if not query:
            self.notify(self._t("Enter a source-search query in the online search field first."), severity="warning")
            self._main_query("#source_query", Input).focus()
            return
        self._main_query("#search_sources", Button).disabled = True
        self._begin_source_search(query, 0)
        self._fetch_sources(query)

    @work(exclusive=True, thread=True)
    def _fetch_sources(self, query: str) -> None:
        config = RadarConfig.load()
        self.call_from_thread(self._begin_source_search, query, len(config.enabled_sources))

        def progress(event: str, source: str, message: str) -> None:
            self.call_from_thread(self._handle_search_progress, event, source, message)

        try:
            summary, _ranked = search_and_ingest(
                query,
                db_path=self.db_path,
                profile_path=DEFAULT_PROFILE,
                semantic=True,
                sources=config.enabled_sources,
                per_source=20,
                config=config,
                progress=progress,
            )
            self.call_from_thread(self._finish_source_search, summary)
        except Exception as exc:
            self.call_from_thread(self._finish_source_search_error, str(exc))

    def action_explore_citations(self) -> None:
        if self._citation_busy:
            self.notify(self._t("Citation exploration is already running."), severity="warning")
            return
        if self._main_query("#search_sources", Button).disabled:
            self.notify(self._t("An online source search is already running; wait for it to finish first."), severity="warning")
            return
        paper_id = self._selected_id()
        if paper_id is None:
            self.notify(self._t("Select a paper first."), severity="warning")
            return
        self._citation_busy = True
        self._main_query("#search_sources", Button).disabled = True
        self._begin_source_search(self._t("Citation graph for paper id={paper_id}", paper_id=paper_id), 0)
        self._search_phase_line = self._t("Preparing bounded citation graph (references, cited-by and related; depth 1, up to 50 nodes)…")
        self._render_search_activity()
        self._fetch_citation_graph(paper_id)

    @work(exclusive=True, thread=True)
    def _fetch_citation_graph(self, paper_id: int) -> None:
        store = PaperStore(self.db_path)
        try:
            def progress(event: str, message: str) -> None:
                self.call_from_thread(self._handle_citation_progress, event, message)

            result = explore_citation_graph(
                store,
                paper_id,
                direction="all",
                depth=1,
                limit=20,
                max_nodes=50,
                config=RadarConfig.load(),
                progress=progress,
            )
            self.call_from_thread(self._finish_citation_explore, result)
        except Exception as exc:
            self.call_from_thread(self._finish_citation_explore_error, str(exc))
        finally:
            store.close()

    def _handle_citation_progress(self, event: str, message: str) -> None:
        self._search_phase_line = message
        if event in {"completed", "cache-hit"}:
            bar = self._main_query("#search_progress", ProgressBar)
            current = int(bar.progress or 0)
            bar.update(total=100, progress=min(90, current + 12))
        elif event == "error":
            self._search_source_messages["citation-warning"] = f"{self._t('warning')}: {message}"
        self._search_source_messages[f"citation-{len(self._search_source_messages)}"] = message
        self._render_search_activity()

    def _finish_citation_explore(self, result) -> None:
        self._citation_busy = False
        self._main_query("#search_sources", Button).disabled = False
        self._search_phase_line = (
            self._t("Citation graph finished: {papers} neighbor(s), {edges} new edge(s), {requests} provider lookup(s), {hits} cache hit(s).", papers=len(result.papers), edges=result.edges_added, requests=result.provider_requests, hits=result.cache_hits)
        )
        if result.warnings:
            self._search_phase_line += " " + " ".join(result.warnings[:1])
        self._search_source_messages = {
            f"paper-{index}": f"id={paper.paper_id}, depth={paper.depth}: {paper.title}"
            for index, paper in enumerate(result.papers[:4], start=1)
        }
        if result.errors:
            self._search_source_messages["errors"] = self._t("{count} provider error(s): {message}", count=len(result.errors), message=result.errors[0])
        self._main_query("#search_progress", ProgressBar).update(total=100, progress=100)
        self._render_search_activity()
        self._personal_model = None
        self.refresh_rows()

    def _finish_citation_explore_error(self, message: str) -> None:
        self._citation_busy = False
        self._main_query("#search_sources", Button).disabled = False
        self._search_phase_line = self._t("Citation exploration failed: {message}", message=message)
        self._render_search_activity()
        self.notify(self._t("Citation exploration failed: {message}", message=message), severity="error")

    def _begin_source_search(self, query: str, source_count: int) -> None:
        """Reset the persistent search activity panel before a new network query."""
        self._search_query = query
        self._search_source_count = max(int(source_count), 0)
        self._search_source_done = set()
        self._search_source_messages = {}
        self._search_phase_line = self._t("Searching {count} source(s)…", count=self._search_source_count)
        self._main_query("#search_progress", ProgressBar).update(total=100, progress=0)
        self._render_search_activity()

    def _localized_phase(self, source: str, message: str) -> str:
        if self.language == "en":
            return message
        patterns = {
            "search": (r"Searching (\d+) online source\(s\) for: (.*)", "Searching {count} online source(s) for: {query}", ("count", "query")),
            "ranking": (r"Ranking (\d+) fetched paper\(s\); this can take longer when semantic scoring is enabled\.", "Ranking {count} fetched paper(s); this can take longer when semantic scoring is enabled.", ("count",)),
            "saving": (r"Saving (\d+) ranked paper\(s\) to the local library\.", "Saving {count} ranked paper(s) to the local library.", ("count",)),
            "complete": (r"Search complete: fetched (\d+); added (\d+); library total (\d+)\.", "Search complete: fetched {fetched}; added {added}; library total {total}.", ("fetched", "added", "total")),
        }
        if source in patterns:
            pattern, template, fields = patterns[source]
            match = re.fullmatch(pattern, message, flags=re.DOTALL)
            if match:
                return self._t(template, **dict(zip(fields, match.groups())))
        return message

    def _handle_search_progress(self, event: str, source: str, message: str) -> None:
        """Render provider and pipeline progress in the main TUI instead of a toast."""
        progress_bar = self._main_query("#search_progress", ProgressBar)

        if event == "phase":
            # Only translate known pipeline prose; provider diagnostics remain literal.
            self._search_phase_line = self._localized_phase(source, message)
            if source == "search":
                progress_bar.update(total=100, progress=0)
            elif source == "ranking":
                progress_bar.update(total=100, progress=78)
            elif source == "saving":
                progress_bar.update(total=100, progress=90)
            elif source == "complete":
                progress_bar.update(total=100, progress=100)
            self._render_search_activity()
            return

        label = {
            "started": self._t("searching"),
            "cache-hit": self._t("cached"),
            "completed": self._t("done"),
            "error": self._t("ERROR"),
            "warning": self._t("warning"),
        }.get(event, event)
        self._search_source_messages[source] = f"{source}: {label} — {message}"

        if event in {"cache-hit", "completed", "error"}:
            self._search_source_done.add(source)
        if self._search_source_count and event in {"started", "cache-hit", "completed", "error"}:
            ratio = len(self._search_source_done) / self._search_source_count
            progress_bar.update(total=100, progress=min(70, round(70 * ratio)))
            self._search_phase_line = (
                self._t("Searching online sources: {done}/{count} finished. Other stages will follow.", done=len(self._search_source_done), count=self._search_source_count)
            )
        self._render_search_activity()

    def _render_search_activity(self) -> None:
        # Keep the query and current phase fixed, then show the latest provider states.
        source_lines = list(self._search_source_messages.values())[-4:]
        lines = [self._t("Query: {query}", query=self._search_query), self._search_phase_line, *source_lines]
        self._main_query("#search_status", Static).update("\n".join(lines))

    def _finish_source_search(self, summary) -> None:
        self._main_query("#search_sources", Button).disabled = False
        errors = self._t("; {count} source error(s)", count=len(summary.source_errors)) if summary.source_errors else ""
        self._search_phase_line = (
            self._t("Finished: fetched {fetched}; added {added}; library total {total}{errors}.", fetched=summary.fetched, added=summary.newly_stored, total=summary.library_total, errors=errors)
        )
        self._main_query("#search_progress", ProgressBar).update(total=100, progress=100)
        self._render_search_activity()
        # The durable result is shown in the activity panel; no disappearing success toast.
        self._personal_model = None
        self.refresh_rows()

    def _finish_source_search_error(self, message: str) -> None:
        self._main_query("#search_sources", Button).disabled = False
        self._search_phase_line = self._t("Search failed: {message}", message=message)
        self._render_search_activity()
        self.notify(self._t("Source search failed: {message}", message=message), severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "language":
            self.set_language(str(event.value))
            return
        if event.select.id in {"status", "sort", "tag"}:
            self.refresh_rows()

    def action_manage_jobs(self) -> None:
        self.push_screen(ScheduleScreen(language=self.language, db_path=self.db_path))

    def action_help(self) -> None:
        self.push_screen(HelpScreen(language=self.language))

    def action_mark_read(self) -> None:
        self._change_status("read")

    def action_to_read(self) -> None:
        self._change_status("to-read")

    def action_dismiss(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, "dismissed", dismiss_reason="user")
            self._personal_model = None
            self.refresh_rows()

    def action_restore(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, "new")
            self._personal_model = None
            self.refresh_rows()

    def action_positive_feedback(self) -> None:
        self._record_feedback(1.0, "useful")

    def action_negative_feedback(self) -> None:
        self._record_feedback(-1.0, "not_relevant")

    def _record_feedback(self, signal: float, reason: str) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            return
        self.store.record_feedback(paper_id, signal, reason=reason)
        self._personal_model = None
        self.notify(self._t("Recorded useful feedback.") if signal > 0 else self._t("Recorded not-relevant feedback."))
        self.refresh_rows()

    def action_tags(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.push_screen(TagScreen(self.store, paper_id, language=self.language), callback=self._tags_closed)

    def _tags_closed(self, _result=None) -> None:
        self._refresh_tag_options()
        self._personal_model = None
        self.refresh_rows()

    def _change_status(self, status: str) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, status)
            self._personal_model = None
            self.refresh_rows()

    def action_download_offline(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            return
        row = self.store.get(paper_id)
        if row is None:
            return
        # Pass only the detached sqlite.Row data into the worker. The worker never
        # touches PaperStore / its SQLite connection.
        self._save_offline(row)

    @work(exclusive=True, thread=True)
    def _save_offline(self, row) -> None:
        try:
            result = save_paper_offline(row, unpaywall_email=RadarConfig.load().unpaywall_email)
        except Exception as exc:
            self.call_from_thread(self._finish_offline_error, str(exc))
            return
        message = (
            self._t("Offline copy ready: {title}", title=row["title"])
            if result["has_pdf"]
            else self._t("Metadata saved; PDF unavailable: {title}", title=row["title"])
        )
        severity = "information" if result["has_pdf"] else "warning"
        self.call_from_thread(self.notify, message, severity=severity)
        self.call_from_thread(self._show_details)

    def _finish_offline_error(self, message: str) -> None:
        self._search_phase_line = self._t("Offline save failed: {message}", message=message)
        self._render_search_activity()
        self.notify(self._search_phase_line, severity="error")

    def action_open(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            return
        row = self.store.get(paper_id)
        if row is None:
            return
        local_pdf = offline_pdf_path(row)
        if local_pdf.exists():
            webbrowser.open(local_pdf.as_uri())
            return
        url = row["pdf_url"] or row["url"]
        if url:
            webbrowser.open(url)

    def action_open_doi(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            return
        row = self.store.get(paper_id)
        if row is None or not row["doi"]:
            self.notify(self._t("The selected paper has no DOI recorded."), severity="warning")
            return
        doi = str(row["doi"]).strip()
        if doi.startswith("http://") or doi.startswith("https://"):
            target = doi
        else:
            target = f"https://doi.org/{doi}"
        webbrowser.open(target)

    def action_focus_search(self) -> None:
        self._main_query("#search", Input).focus()

    def action_focus_status(self) -> None:
        self._main_query("#status", Select).focus()

    def action_focus_sort(self) -> None:
        self._main_query("#sort", Select).focus()

    def action_focus_tag(self) -> None:
        self._main_query("#tag", Select).focus()

    def _refresh_tag_options(self) -> None:
        tag_select = self._main_query("#tag", Select)
        current = str(tag_select.value or "__all_tags__")
        options = [(self._t("All tags"), "__all_tags__")] + [(tag, tag) for tag in self.store.all_tags()]
        tag_select.set_options(options)
        if current in {value for _, value in options}:
            tag_select.value = current
