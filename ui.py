from __future__ import annotations

import json
from pathlib import Path

from storage.sqlite import PaperStore, STATUSES

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Select, Static
from textual.binding import Binding


class LitRadarApp(App[None]):
    """Compact interactive research inbox for LitRadar."""

    TITLE = "LitRadar"
    SUB_TITLE = "Research Inbox"
    CSS_PATH = "ui.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "mark_read", "Read"),
        Binding("t", "to_read", "To Read"),
        Binding("d", "dismiss", "Dismiss"),
        Binding("u", "restore", "Restore"),
        Binding("o", "open", "Open"),
        Binding("/", "focus_search", "Search"),
        Binding("f", "focus_status", "Filter"),
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
        with Horizontal(id="main"):
            yield DataTable(id="papers", cursor_type="row", zebra_stripes=True)
            with Vertical(id="details"):
                yield Static("Select a paper", id="details_title")
                yield Static("", id="details_body")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#papers", DataTable)
        table.add_columns("ID", "Score", "Status", "Year", "Title")
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
        self.current_rows = self.store.list_papers(limit=200, status=status, query=query, sort="relevance_score")
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
        body = (
            f"Status: {row['status']}\n"
            f"Score: {row['relevance_score']:.3f}\n"
            f"Source: {row['source']}\n"
            f"Published: {row['published_at'] or 'n/a'}\n"
            f"Venue: {row['venue'] or 'n/a'}\n"
            f"Tags: {tags}\n\n"
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
        if event.select.id == "status":
            self.refresh_rows()

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

    def _change_status(self, status: str) -> None:
        paper_id = self._selected_id()
        if paper_id is not None:
            self.store.set_status(paper_id, status)
            self.refresh_rows()

    def action_open(self) -> None:
        paper_id = self._selected_id()
        if paper_id is None:
            return
        row = self.store.get(paper_id)
        if row is None:
            return
        url = row["url"] or row["pdf_url"]
        if url:
            import webbrowser
            webbrowser.open(url)

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_status(self) -> None:
        self.query_one("#status", Select).focus()
