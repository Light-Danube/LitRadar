from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from storage.sqlite import PaperStore, SORT_CHOICES, STATUSES
from offline import is_available_offline, offline_pdf_path, save_paper_offline

from textual.app import App, ComposeResult
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static


SORT_LABELS = {
    "relevance_score": "Relevance",
    "recent": "Published ↓",
    "published_oldest": "Published ↑",
    "newest_added": "Added ↓",
    "title": "Title A–Z",
    "score": "Score ↓",
    "citations": "Citations ↓",
}


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
            "S       focus sort\n\n"
            "[b]Workflow[/b]\n"
            "T       mark To Read\n"
            "R       mark Read\n"
            "D       dismiss\n"
            "U       restore\n"
            "G       edit tags\n"
            "L       save current paper offline\n"
            "O       open local PDF or paper URL\n\n"
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
        Binding("g", "tags", "Tags"),
        Binding("l", "download_offline", "Offline"),
        Binding("o", "open", "Open"),
        Binding("/", "focus_search", "Search"),
        Binding("f", "focus_status", "Filter"),
        Binding("s", "focus_sort", "Sort"),
        Binding("k", "focus_tag", "Tag"),
    ]

    def __init__(self, db_path: str | Path) -> None:
        super().__init__()
        self.db_path = str(db_path)
        self.store = PaperStore(db_path)
        self.current_rows = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="toolbar"):
            yield Input(placeholder="Search title, abstract, venue…", id="search")
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
            yield Select([], value="__all_tags__", id="tag", allow_blank=False)
            yield Static("Papers: 0", id="library_count")
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
        self.current_rows = self.store.list_papers(limit=200, status=status, query=query, tag=tag, sort=sort)
        table = self.query_one("#papers", DataTable)
        table.clear(columns=False)
        for row in self.current_rows:
            year = (row["published_at"] or "")[:4] or "—"
            table.add_row(str(row["id"]), f"{row['relevance_score']:.3f}", row["status"], year, row["title"])
        self._show_details()

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
        body = (
            f"Status: {row['status']}\n"
            f"Score: {row['relevance_score']:.3f}\n"
            f"Source: {row['source']}\n"
            f"Published: {row['published_at'] or 'n/a'}\n"
            f"Venue: {row['venue'] or 'n/a'}\n"
            f"Citations: {row['citation_count']}\n"
            f"Tags: {tags}\n"
            f"Source tags: {source_tags}\n"
            f"Offline PDF: {offline_pdf_path(row) if is_available_offline(row) else 'not saved'}\n\n"
            f"{row['abstract'] or '(no abstract)'}"
        )
        self.query_one("#details_title", Static).update(row["title"])
        self.query_one("#details_body", Static).update(body)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_details()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self.refresh_rows()

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
            self.refresh_rows()

    def action_restore(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, "new")
            self.refresh_rows()

    def action_tags(self) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.push_screen(TagScreen(self.store, paper_id), callback=lambda _: self.refresh_rows())

    def _change_status(self, status: str) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, status)
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
        result = save_paper_offline(row)
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
