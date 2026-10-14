from __future__ import annotations

import importlib.util
import string

import pytest

from ui_locales import UK, normalize_language, tr


def test_locale_templates_preserve_interpolation_fields():
    formatter = string.Formatter()
    for english, ukrainian in UK.items():
        assert {field for _, field, _, _ in formatter.parse(english) if field} == {
            field for _, field, _, _ in formatter.parse(ukrainian) if field
        }
    assert normalize_language('uk_UA') == 'uk'
    assert normalize_language('fr') == 'en'
    assert tr('uk', 'Query: {query}', query='[bold] literal') == 'Запит: [bold] literal'


@pytest.mark.skipif(importlib.util.find_spec('textual') is None, reason='Textual UI dependency is optional')
@pytest.mark.asyncio
async def test_ukrainian_chrome_runtime_switch_and_modal_localization(tmp_path):
    from textual.widgets import Button, Input, Select, Static
    from ui import HelpScreen, LitRadarApp

    app = LitRadarApp(tmp_path / 'library.sqlite3', language='uk')
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        assert app.query_one('#search', Input).placeholder.startswith('Фільтр бібліотеки')
        assert str(app.query_one('#search_sources', Button).label) == 'Знайти публікації'
        assert str(app.query_one('#library_count', Static).renderable) == 'Бібліотека: 0 | Вибірка: 0'
        assert app._bindings.get_bindings_for_key('q')[0].description == 'Вийти'
        for key, description in [('question_mark', 'Довідка'), ('slash', 'Пошук')]:
            bindings = app._bindings.get_bindings_for_key(key)
            assert len(bindings) == 1
            assert bindings[0].description == description
        app.query_one('#source_query', Input).value = 'unchanged query'
        app.query_one('#status', Select).value = 'read'
        app.query_one('#language', Select).value = 'en'
        await pilot.pause()
        assert app.language == 'en'
        assert app.query_one('#source_query', Input).value == 'unchanged query'
        assert app.query_one('#status', Select).value == 'read'
        assert str(app.query_one('#search_sources', Button).label) == 'Fetch papers'
        app.query_one('#language', Select).value = 'uk'
        await pilot.pause()
        app.action_help()
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        assert 'клавіатурна довідка' in str(app.screen.query_one('#help_body', Static).renderable)
        # Background completion must update the library even when a modal is visible.
        app.refresh_rows()
        await pilot.press('escape')
        await pilot.pause()


@pytest.mark.skipif(importlib.util.find_spec('textual') is None, reason='Textual UI dependency is optional')
@pytest.mark.asyncio
async def test_progress_localizes_labels_and_preserves_provider_diagnostics(tmp_path):
    from textual.widgets import Static
    from ui import LitRadarApp

    app = LitRadarApp(tmp_path / 'library.sqlite3', language='uk')
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        app._begin_source_search('запит', 2)
        app._handle_search_progress('completed', 'openalex', '[literal] received 4 papers')
        status = str(app.query_one('#search_status', Static).renderable)
        assert 'Запит: запит' in status
        assert 'openalex: готово — [literal] received 4 papers' in status
        assert 'завершено 1/2' in status


@pytest.mark.skipif(importlib.util.find_spec('textual') is None, reason='Textual UI dependency is optional')
@pytest.mark.asyncio
async def test_paper_titles_tags_and_status_keep_data_literal(tmp_path):
    from sources.base import Paper
    from textual.widgets import DataTable, Static
    from ui import LitRadarApp, TagScreen

    app = LitRadarApp(tmp_path / 'library.sqlite3', language='uk')
    title = '[bold] A literal paper [/bold]'
    paper_id = app.store.upsert_paper(Paper(source='synthetic', title=title, abstract='[red] буквальний текст'), relevance_score=1.0, matched_groups={})
    app.store.set_tags(paper_id, ['[blue]literal'])
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        assert str(app.query_one('#details_title', Static).renderable) == title
        body = app.query_one('#details_body', Static).renderable.plain
        assert 'Статус: Нові' in body
        assert '[red] буквальний текст' in body
        assert '[blue]literal' in body
        assert app.query_one('#papers', DataTable).get_cell_at((0, 2)) == 'Нові'
        assert app.store.get(paper_id)['status'] == 'new'
        app.action_tags()
        await pilot.pause()
        assert isinstance(app.screen, TagScreen)
        assert str(app.screen.query_one('#tag_existing', Static).renderable) == 'Наявні теги: [blue]literal'
        await pilot.press('escape')


def test_known_pipeline_phases_are_translated_without_altering_diagnostics(tmp_path):
    if importlib.util.find_spec('textual') is None:
        pytest.skip('Textual UI dependency is optional')
    from ui import LitRadarApp
    app = LitRadarApp(tmp_path / 'library.sqlite3', language='uk')
    try:
        assert app._localized_phase('ranking', 'Ranking 4 fetched paper(s); this can take longer when semantic scoring is enabled.').startswith('Ранжування отриманих публікацій: 4')
        assert app._localized_phase('saving', 'Saving 4 ranked paper(s) to the local library.') == 'Збереження ранжованих публікацій у бібліотеці: 4.'
        assert app._localized_phase('ranking', '[raw provider diagnostic]') == '[raw provider diagnostic]'
    finally:
        app.store.close()


@pytest.mark.skipif(importlib.util.find_spec('textual') is None, reason='Textual UI dependency is optional')
@pytest.mark.asyncio
async def test_language_change_retains_selected_paper_and_jobs_are_localized(tmp_path, monkeypatch):
    import subprocess
    from sources.base import Paper
    from textual.widgets import Button, DataTable, Input, Select, Static
    from ui import LitRadarApp, ScheduleScreen

    monkeypatch.setattr('ui.subprocess.run', lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, '[literal] scheduler output', ''))
    app = LitRadarApp(tmp_path / 'library.sqlite3', language='en')
    for index in range(2):
        app.store.upsert_paper(Paper(source='synthetic', title=f'Paper {index}'),
                              relevance_score=float(index), matched_groups={})
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert app.query_one('#search', Input).region.width >= 30
        assert app.query_one('#source_query', Input).region.width >= 20
        for selector in ('#status', '#sort', '#tag', '#library_count', '#search_sources', '#language'):
            region = app.query_one(selector).region
            assert 0 <= region.x < region.right <= 80
        table = app.query_one('#papers', DataTable)
        table.move_cursor(row=1)
        selected_id = app._selected_id()
        app.query_one('#language', Select).value = 'uk'
        await pilot.pause()
        assert app._selected_id() == selected_id
        app.action_manage_jobs()
        await app.workers.wait_for_complete()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ScheduleScreen)
        assert str(screen.query_one('#schedule_title', Static).renderable) == 'Заплановані завдання'
        assert str(screen.query_one('#schedule_remove_digest', Button).label) == 'Вимкнути дайджест'
        assert str(screen.query_one('#schedule_status', Static).renderable) == '[literal] scheduler output'
        # Focus scrolls the last button into view even on a short terminal.
        screen.query_one('#schedule_close', Button).focus()
        await pilot.pause()
        await pilot.press('enter')
        assert not isinstance(app.screen, ScheduleScreen)
