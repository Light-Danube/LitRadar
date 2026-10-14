"""Synthetic-vector unit tests: these do not evaluate a downloaded language model."""
from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from ranking.semantic_workspace import LocalSentenceTransformerEmbedder, SemanticWorkspace


class Vectors:
    model_name = "synthetic-test-vectors"

    def __init__(self, values):
        self.values = values
        self.calls = []

    def encode(self, texts):
        self.calls.append(texts)
        return np.asarray(self.values)


def papers(count):
    return [{"id": i + 1, "title": f"Fixture {i + 1}", "abstract": "public abstract",
             "notes": "private note never embedded"} for i in range(count)]


def test_cosine_edges_are_undirected_ephemeral_and_not_rescaled():
    model = Vectors([[1, 0], [0.9, 0.1], [-1, 0], [0, 0]])
    result = SemanticWorkspace(model).analyze(papers(4))
    assert [(e["source"], e["target"], e["type"]) for e in result["edges"]] == [("1", "2", "related")]
    assert result["edges"][0]["similarity"] == pytest.approx(0.993884)
    assert result["edges"][0]["provenance"][0]["ephemeral"] is True
    assert result["edges"][0]["provider"] == "embedding:synthetic-test-vectors"
    assert all("private note" not in text for text in model.calls[0])
    assert sorted(c["size"] for c in result["clusters"]) == [1, 1, 2]


def test_complete_link_does_not_chain_dissimilar_endpoints():
    # Adjacent vectors meet 0.7; the first and last are orthogonal.
    model = Vectors([[1, 0], [1, 1], [0, 1]])
    result = SemanticWorkspace(model, threshold=0.7).analyze(papers(3))
    assert len(result["edges"]) == 2
    assert sorted(c["size"] for c in result["clusters"]) == [1, 2]


def test_neighbor_cap_bounds_degree_and_ties_are_deterministic():
    model = Vectors([[1, 0]] * 6)
    workspace = SemanticWorkspace(model, max_neighbors=1)
    result = workspace.analyze(list(reversed(papers(6))))
    assert [(e["source"], e["target"]) for e in result["edges"]] == [("1", "2"), ("3", "4"), ("5", "6")]
    assert result == workspace.analyze(papers(6))


@pytest.mark.parametrize("values", [[[1]], [[float("nan"), 0]], [[float("inf"), 1]], [1, 2], [[]]])
def test_invalid_embedder_outputs_fail_explicitly(values):
    count = 2 if values == [[1]] else 1
    with pytest.raises(ValueError):
        SemanticWorkspace(Vectors(values)).analyze(papers(count))


@pytest.mark.parametrize("threshold", [0, -1, 1.1, float("nan")])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        SemanticWorkspace(Vectors([]), threshold=threshold)


def test_empty_bounded_unique_and_input_clipping():
    model = Vectors([[1]])
    workspace = SemanticWorkspace(model)
    assert workspace.analyze([])["edges"] == []
    assert not model.calls
    with pytest.raises(ValueError, match="200"):
        workspace.analyze(papers(201))
    with pytest.raises(ValueError, match="unique"):
        workspace.analyze([papers(1)[0]] * 2)
    long_paper = {"id": 1, "title": "x" * 9000}
    workspace.analyze([long_paper])
    assert len(model.calls[0][0]) == 6000


def test_local_model_loading_is_lazy_offline_and_disallows_remote_code(tmp_path, monkeypatch):
    calls = []

    class Model:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def encode(self, texts, **kwargs):
            return [[1, 0] for _ in texts]

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=Model))
    embedder = LocalSentenceTransformerEmbedder(tmp_path)
    assert calls == []
    assert embedder.encode([]).shape == (0, 0)
    assert calls == []
    embedder.encode(["title"])
    assert calls[0][1] == {"local_files_only": True, "trust_remote_code": False,
                           "model_kwargs": {"use_safetensors": True}}
    embedder.encode(["again"])
    assert len(calls) == 1
    with pytest.raises(ValueError, match="local model"):
        LocalSentenceTransformerEmbedder(tmp_path / "not-there")
