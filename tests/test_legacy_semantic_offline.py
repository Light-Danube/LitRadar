"""Legacy scoring never provisions models; no real model/dependency is loaded."""
import sys
from types import SimpleNamespace

import numpy as np
import pytest

import cli
import pipeline
from ranking.embeddings import SentenceTransformerEmbedder
from ranking.keywords import KeywordGroup, KeywordProfile
from sources.base import Paper


def test_local_model_loading_is_lazy_offline_and_reused(monkeypatch):
    calls = []

    class Model:
        def __init__(self, name, **kwargs):
            assert kwargs == {"local_files_only": True, "trust_remote_code": False}
            calls.append((name, kwargs))

        def encode(self, texts, **kwargs):
            assert kwargs == {"batch_size": 2, "normalize_embeddings": True, "show_progress_bar": False}
            return [[1, 0] for _ in texts]

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=Model))
    embedder = SentenceTransformerEmbedder("synthetic-local-model", batch_size=2)
    assert calls == []
    np.testing.assert_array_equal(embedder.encode(["one", "two"]), [[1, 0], [1, 0]])
    np.testing.assert_array_equal(embedder.encode(["three"]), [[1, 0]])
    assert len(calls) == 1
    assert calls[0][0] == "synthetic-local-model"


@pytest.mark.parametrize("error_type", [OSError, ValueError])
def test_missing_local_model_falls_back_without_echoing_private_loader_error(monkeypatch, capsys, error_type):
    calls = []

    def unavailable(name, **kwargs):
        assert kwargs == {"local_files_only": True, "trust_remote_code": False}
        calls.append(name)
        raise error_type("SYNTHETIC_PRIVATE_PATH_AND_URL_MUST_NOT_BE_DISPLAYED")

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=unavailable))
    papers = [Paper(source="fixture", title="Synthetic context")]
    profile = KeywordProfile([KeywordGroup("context", 1, ("context",))])
    expected = pipeline._rank(papers, profile, semantic=False)
    progress = []
    assert pipeline._rank(papers, profile, semantic=True, progress=lambda *event: progress.append(event)) == expected
    assert cli._rank(papers, profile, semantic=True) == expected
    assert len(calls) == 2
    assert progress == [("warning", "ranking", "semantic scoring unavailable; using keywords")]
    error = capsys.readouterr().err
    assert "not available locally" in error and "--no-semantic" in error
    assert "SYNTHETIC_PRIVATE" not in error


def test_keyword_only_scoring_does_not_load_a_model(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Keyword-only scoring attempted model loading")

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=unexpected))
    papers = [Paper(source="fixture", title="Synthetic context")]
    profile = KeywordProfile([KeywordGroup("context", 1, ("context",))])
    assert len(pipeline._rank(papers, profile, semantic=False)) == 1
    assert len(cli._rank(papers, profile, semantic=False)) == 1
