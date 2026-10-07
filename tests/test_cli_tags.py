from __future__ import annotations

from cli import build_parser


def test_tags_parser_supports_add_remove_set() -> None:
    parser = build_parser()

    args = parser.parse_args(["tags", "42", "sarcasm", "context"])
    assert args.tags == ["sarcasm", "context"]
    assert args.remove is None
    assert args.set_tags is None

    args = parser.parse_args(["tags", "42", "--remove", "broad", "old"])
    assert args.tags == []
    assert args.remove == ["broad", "old"]

    args = parser.parse_args(["tags", "42", "--set", "a,b,c"])
    assert args.set_tags == "a,b,c"
