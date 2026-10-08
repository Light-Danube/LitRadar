from __future__ import annotations

from config import _split_sources


def test_split_sources_deduplicates_and_normalizes():
    assert _split_sources(" OpenAlex, semantic_scholar,openalex, arxiv ") == (
        "openalex",
        "semantic_scholar",
        "arxiv",
    )
