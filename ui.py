from __future__ import annotations

import json
import re
import webbrowser
from pathlib import Path

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.personalization import build_model, explain_candidate, neutral_results, score_rows
from storage.sqlite import PaperStore, SORT_CHOICES, STATUSES
from offline import is_available_offline, offline_pdf_path, save_paper_offline
from pipeline import search_and_ingest

from rich.text import Text
from textual.app import App, ComposeResult
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
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

    def compose(self) -> ComposeResult:
        yield Static(
            "[b]LitRadar — keyboard help[/b]\n\n"
            "[b]Navigation[/b]\n"
            "↑ / ↓   select paper\n"
            "Enter   select row\n"
            "/       focus search\n"
            "F       focus status filter\n"
            "S       focus sort\n"
            "Search box filters the saved library locally.\n"
            "Online search box + Fetch / Ctrl+Enter queries enabled providers.\n"
            "The progress panel below shows provider activity, ranking, and saving.\n\n"
            "[b]Workflow[/b]\n"
            "T       mark To Read\n"
            "R       mark Read\n"
            "Y       useful / positive feedback\n"
            "N       not relevant / negative feedback\n"
            "D       dismiss\n"
            "U       restore\n"
            "G       edit tags\n"
            "L       save current paper offline\n"
            "O       open local PDF or paper URL\n"
            "S       includes Personalized sort\n\n"
            "?       this help\n"
            "Q / Esc close help / quit\n",
            id="help_body",
        )

    def action_close(self) -> None:
        self.dismiss()


class TagScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, store: PaperStore, paper_id: int) -> None:
        super().__init__()
        self.store = store
        self.paper_id = paper_id

    def compose(self) -> ComposeResult:
        row = self.store.get(self.paper_id)
        current = ", ".join(json.loads(row["tags_json"] or "[]")) if row else ""
        existing = ", ".join(self.store.all_tags()) or "(none yet)"
        with Vertical(id="tag_dialog"):
            yield Static("[b]Edit tags[/b]", id="tag_title")
            yield Static(f"Existing tags: {existing}", id="tag_existing")
            yield Input(value=current, placeholder="tag-one, tag-two, …", id="tag_input")
            with Horizontal(id="tag_buttons"):
                yield Button("Save", id="tag_save", variant="primary")
                yield Button("Cancel", id="tag_cancel")

    def on_mount(self) -> None:
        self.query_one("#tag_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tag_save":
            raw = self.query_one("#tag_input", Input).value
            tags = [part.strip() for part in raw.split(",") if part.strip()]
            self.store.set_tags(self.paper_id, tags)
            self.dismiss()
        elif event.button.id == "tag_cancel":
            self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tag_input":
            raw = event.value
            tags = [part.strip() for part in raw.split(",") if part.strip()]
            self.store.set_tags(self.paper_id, tags)
            self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class LitRadarApp(App[None]):
    """Interactive research inbox for LitRadar."""

    TITLE = "LitRadar"
    SUB_TITLE = "Research Inbox"
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
    ]

    def __init__(self, db_path: str | Path) -> None:
        super().__init__()
        self.db_path = str(db_path)
        self.store = PaperStore(db_path)
        self.current_rows = []
        self.current_display_scores: dict[int, float] = {}
        self.profile = KeywordProfile.from_json(Path(__file__).resolve().parent / "research_profile.json")
        self._personal_model = None
        self._personalization_model_active = False
        self._search_query = ""
        self._search_source_count = 0
        self._search_source_done: set[str] = set()
        self._search_source_messages: dict[str, str] = {}
        self._search_phase_line = "Ready. Enter a query above; provider activity and the final summary will appear here."

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="toolbar"):
            yield Input(placeholder="Filter saved library by title/abstract/notes…", id="search")
            yield Select(
                [(label.replace("-", " ").title(), label) for label in ["all", *STATUSES]],
                value="all",
                id="status",
                allow_blank=False,
            )
            yield Select(
                [(label, key) for key, label in SORT_LABELS.items()],
                value="relevance_score",
                id="sort",
                allow_blank=False,
            )
            yield Select([("All tags", "__all_tags__")], value="__all_tags__", id="tag", allow_blank=False)
            yield Static("Papers: 0", id="library_count")
        with Horizontal(id="actionbar"):
            yield Input(placeholder="Search online sources…", id="source_query")
            yield Button("Fetch papers", id="search_sources", variant="primary")
        with Horizontal(id="search_progress_row"):
            yield ProgressBar(total=100, show_eta=False, show_percentage=True, id="search_progress")
            yield Static(
                "Ready. Enter a query above; provider activity and the final summary will appear here.",
                id="search_status",
                markup=False,
            )
        with Horizontal(id="main"):
            yield DataTable(id="papers", cursor_type="row", zebra_stripes=True)
            with Vertical(id="details"):
                yield Static("Select a paper", id="details_title")
                yield Static("", id="details_body")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#papers", DataTable)
        table.add_columns("ID", "Score", "Status", "Year", "Title")
        self._refresh_tag_options()
        self.refresh_rows()

    def on_unmount(self) -> None:
        self.store.close()

    def _selected_id(self) -> int | None:
        table = self.query_one("#papers", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.current_rows):
            return None
        return int(self.current_rows[table.cursor_row]["id"])

    def refresh_rows(self) -> None:
        query = self.query_one("#search", Input).value.strip() or None
        status = str(self.query_one("#status", Select).value or "all")
        sort = str(self.query_one("#sort", Select).value or "relevance_score")
        tag_value = str(self.query_one("#tag", Select).value or "__all_tags__")
        tag = None if tag_value == "__all_tags__" else tag_value
        library_total = self.store.total_count()
        view_total = self.store.total_count(status=status, query=query, tag=tag)
        self.query_one("#library_count", Static).update(f"Library: {library_total} | View: {view_total}")

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

        table = self.query_one("#papers", DataTable)
        table.clear(columns=False)
        for row in self.current_rows:
            year = (row["published_at"] or "")[:4] or "—"
            display_score = self.current_display_scores.get(int(row["id"]), float(row["relevance_score"] or 0.0))
            table.add_row(str(row["id"]), f"{display_score:.3f}", row["status"], year, row["title"])
        self._show_details()

    def _profile(self) -> object:
        return self.profile

    def _show_details(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            self.query_one("#details_title", Static).update("No paper selected")
            self.query_one("#details_body", Static).update("")
            return
        row = self.store.get(paper_id)
        if row is None:
            return
        tags = ", ".join(json.loads(row["tags_json"] or "[]")) or "—"
        source_tags = ", ".join(json.loads(row["source_tags_json"] or "[]")) or "—"
        abstract_value = row["abstract"] or "(no abstract)"
        body = (
            f"Status: {row['status']}\n"
            f"Base score: {row['relevance_score']:.3f}\n"
            f"Displayed score: {self.current_display_scores.get(int(row['id']), float(row['relevance_score'] or 0.0)):.3f}\n"
            f"Source: {row['source']}\n"
            f"Published: {row['published_at'] or 'n/a'}\n"
            f"Venue: {row['venue'] or 'n/a'}\n"
            f"DOI: {row['doi'] or 'n/a'}\n"
            f"Citations: {row['citation_count']}\n"
            f"References: {row['reference_count'] if row['reference_count'] is not None else 'n/a'}\n"
            f"Influential citations: {row['influential_citation_count'] if row['influential_citation_count'] is not None else 'n/a'}\n"
            f"Tags: {tags}\n"
            f"Source tags: {source_tags}\n"
            f"Offline PDF: {offline_pdf_path(row) if is_available_offline(row) else 'not saved'}\n\n"
            f"{abstract_value}"
        )
        if str(self.query_one("#sort", Select).value) == "personalized" and self._personalization_model_active and self._personal_model is not None:
            config = RadarConfig.load()
            explanation = explain_candidate(
                row,
                self._personal_model,
                self._profile(),
                weight=config.personalized_weight,
            )
            body += f"\n\nPersonalized recommendation: {explanation}"
        elif str(self.query_one("#sort", Select).value) == "personalized":
            body += "\n\nPersonalized recommendation: not active yet; add more feedback or enable personalization."
        self.query_one("#details_title", Static).update(row["title"])
        search_query = self.query_one("#search", Input).value.strip()
        # Construct Rich Text from literal content so abstracts containing
        # markup-like characters remain safe to display.
        self.query_one("#details_body", Static).update(
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
        query = self.query_one("#source_query", Input).value.strip()
        if not query:
            self.notify("Enter a source-search query in the online search field first.", severity="warning")
            self.query_one("#source_query", Input).focus()
            return
        self.query_one("#search_sources", Button).disabled = True
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
                profile_path=Path(__file__).resolve().parent / "research_profile.json",
                semantic=True,
                sources=config.enabled_sources,
                per_source=20,
                config=config,
                progress=progress,
            )
            self.call_from_thread(self._finish_source_search, summary)
        except Exception as exc:
            self.call_from_thread(self._finish_source_search_error, str(exc))

    def _begin_source_search(self, query: str, source_count: int) -> None:
        """Reset the persistent search activity panel before a new network query."""
        self._search_query = query
        self._search_source_count = max(int(source_count), 0)
        self._search_source_done = set()
        self._search_source_messages = {}
        self._search_phase_line = f"Searching {self._search_source_count} source(s)…"
        self.query_one("#search_progress", ProgressBar).update(total=100, progress=0)
        self._render_search_activity()

    def _handle_search_progress(self, event: str, source: str, message: str) -> None:
        """Render provider and pipeline progress in the main TUI instead of a toast."""
        progress_bar = self.query_one("#search_progress", ProgressBar)

        if event == "phase":
            self._search_phase_line = message
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
            "started": "searching",
            "cache-hit": "cached",
            "completed": "done",
            "error": "ERROR",
            "warning": "warning",
        }.get(event, event)
        self._search_source_messages[source] = f"{source}: {label} — {message}"

        if event in {"cache-hit", "completed", "error"}:
            self._search_source_done.add(source)
        if self._search_source_count and event in {"started", "cache-hit", "completed", "error"}:
            ratio = len(self._search_source_done) / self._search_source_count
            progress_bar.update(total=100, progress=min(70, round(70 * ratio)))
            self._search_phase_line = (
                f"Searching online sources: {len(self._search_source_done)}/"
                f"{self._search_source_count} finished. Other stages will follow."
            )
        self._render_search_activity()

    def _render_search_activity(self) -> None:
        # Keep the query and current phase fixed, then show the latest provider states.
        source_lines = list(self._search_source_messages.values())[-4:]
        lines = [f"Query: {self._search_query}", self._search_phase_line, *source_lines]
        self.query_one("#search_status", Static).update("\n".join(lines))

    def _finish_source_search(self, summary) -> None:
        self.query_one("#search_sources", Button).disabled = False
        errors = f"; {len(summary.source_errors)} source error(s)" if summary.source_errors else ""
        self._search_phase_line = (
            f"Finished: fetched {summary.fetched}; added {summary.newly_stored}; "
            f"library total {summary.library_total}{errors}."
        )
        self.query_one("#search_progress", ProgressBar).update(total=100, progress=100)
        self._render_search_activity()
        # The durable result is shown in the activity panel; no disappearing success toast.
        self._personal_model = None
        self.refresh_rows()

    def _finish_source_search_error(self, message: str) -> None:
        self.query_one("#search_sources", Button).disabled = False
        self._search_phase_line = f"Search failed: {message}"
        self._render_search_activity()
        self.notify(f"Source search failed: {message}", severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in {"status", "sort", "tag"}:
            self.refresh_rows()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

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
        self.notify("Recorded useful feedback." if signal > 0 else "Recorded not-relevant feedback.")
        self.refresh_rows()

    def action_tags(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.push_screen(TagScreen(self.store, paper_id), callback=lambda _: self.refresh_rows())

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
        result = save_paper_offline(row, unpaywall_email=RadarConfig.load().unpaywall_email)
        message = (
            f"Offline copy ready: {row['title']}"
            if result["has_pdf"]
            else f"Metadata saved; PDF unavailable: {row['title']}"
        )
        severity = "information" if result["has_pdf"] else "warning"
        self.call_from_thread(self.notify, message, severity=severity)
        self.call_from_thread(self._show_details)

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
            self.notify("The selected paper has no DOI recorded.", severity="warning")
            return
        doi = str(row["doi"]).strip()
        if doi.startswith("http://") or doi.startswith("https://"):
            target = doi
        else:
            target = f"https://doi.org/{doi}"
        webbrowser.open(target)

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_status(self) -> None:
        self.query_one("#status", Select).focus()

    def action_focus_sort(self) -> None:
        self.query_one("#sort", Select).focus()

    def action_focus_tag(self) -> None:
        self.query_one("#tag", Select).focus()

    def _refresh_tag_options(self) -> None:
        tag_select = self.query_one("#tag", Select)
        current = str(tag_select.value or "__all_tags__")
        options = [("All tags", "__all_tags__")] + [(tag, tag) for tag in self.store.all_tags()]
        tag_select.set_options(options)
        if current in {value for _, value in options}:
            tag_select.value = current
