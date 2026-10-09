from cli import build_parser


def test_note_editor_and_export_notes_commands_are_documented():
    parser = build_parser()
    note = parser.parse_args(["note", "8", "--edit"])
    assert note.edit is True
    assert note.paper_id == 8
    export = parser.parse_args(["export-notes", "--status", "read", "--output", "draft.md"])
    assert export.status == "read"
    assert export.output == "draft.md"
    parser.print_help()
