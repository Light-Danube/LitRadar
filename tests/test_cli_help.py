from __future__ import annotations

from cli import build_parser


def test_root_help_mentions_core_commands(capsys):
    parser = build_parser()
    try:
        parser.parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "list" in output
    assert "dismiss" in output
    assert "ui" in output
    assert "Examples:" in output


def test_list_help_has_filters(capsys):
    parser = build_parser()
    try:
        parser.parse_args(["list", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "--status" in output
    assert "--query" in output
    assert "--min-score" in output


def test_root_help_mentions_offline_and_bibtex(capsys):
    from cli import build_parser
    build_parser().print_help()
    output = capsys.readouterr().out
    assert "export-bibtex" in output
    assert "download" in output
