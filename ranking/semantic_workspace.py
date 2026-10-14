"""Opt-in, ephemeral local semantic exploration; never writes citation records."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np
import hashlib

from .embeddings import TextEmbedder


class LocalSentenceTransformerEmbedder:
    """Load an explicitly supplied local model without fetching remote artifacts."""

    def __init__(self, model_path: str | Path):
        path = Path(model_path).resolve()
        if not path.is_dir():
            raise ValueError("Semantic exploration requires an existing local model directory")
        self.model_name = path.name
        self._path = path
        self._model = None

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("Install requirements-semantic.txt for optional local semantic exploration") from exc
            self._model = SentenceTransformer(
                str(self._path), local_files_only=True, trust_remote_code=False,
                model_kwargs={"use_safetensors": True},
            )
        return np.asarray(self._model.encode(
            list(texts), batch_size=16, normalize_embeddings=True, show_progress_bar=False,
        ), dtype=np.float32)


class SemanticWorkspace:
    """Bounded cosine edges and deterministic complete-link reading clusters.

    The caller owns the OFF-default feature flag. Injecting an embedder permits
    offline algorithm tests without importing sentence-transformers or a model.
    Similarity is raw cosine, not a citation claim or a calibrated probability.
    """

    def __init__(self, embedder: TextEmbedder, *, threshold: float = 0.72, max_neighbors: int = 5):
        if not np.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("Semantic threshold must be greater than zero and at most one")
        if not isinstance(max_neighbors, int) or not 1 <= max_neighbors <= 20:
            raise ValueError("Semantic max_neighbors must be between 1 and 20")
        self.embedder = embedder
        self.threshold = float(threshold)
        self.max_neighbors = max_neighbors

    def analyze(self, papers: Sequence[dict[str, Any]]) -> dict[str, Any]:
        if len(papers) > 200:
            raise ValueError("Semantic exploration is limited to 200 papers per request")
        prepared = sorted(papers, key=lambda paper: int(paper["id"]))
        ids = [int(paper["id"]) for paper in prepared]
        if len(ids) != len(set(ids)):
            raise ValueError("Semantic exploration requires unique paper IDs")
        metadata = {"method": "embedding", "model": self.embedder.model_name,
                    "threshold": self.threshold, "evaluated_nodes": len(prepared)}
        if not prepared:
            return {**metadata, "edges": [], "clusters": []}
        # Deliberately omit user notes and annotation content from model input.
        texts = [(str(p.get("title") or "") + "\n" + str(p.get("abstract") or ""))[:6000]
                 for p in prepared]
        matrix = np.asarray(self.embedder.encode(texts), dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[0] != len(prepared) or not matrix.shape[1]:
            raise ValueError("Embedder must return one nonempty vector per paper")
        if not np.isfinite(matrix).all():
            raise ValueError("Embedder returned non-finite values")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if not np.isfinite(norms).all():
            raise ValueError("Embedding norms overflowed")
        normalized = np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)
        similarities = np.clip(normalized @ normalized.T, -1, 1)
        candidates = sorted(
            ((float(similarities[i, j]), i, j) for i in range(len(prepared))
             for j in range(i + 1, len(prepared)) if similarities[i, j] >= self.threshold),
            key=lambda pair: (-pair[0], ids[pair[1]], ids[pair[2]]),
        )
        provider = "embedding:" + self.embedder.model_name
        if len(provider)>80:
            provider = "embedding:"+self.embedder.model_name[:60]+":"+hashlib.sha256(self.embedder.model_name.encode()).hexdigest()[:8]
        degree = [0] * len(prepared)
        edges = []
        for similarity, i, j in candidates:
            if degree[i] >= self.max_neighbors or degree[j] >= self.max_neighbors:
                continue
            degree[i] += 1
            degree[j] += 1
            edges.append({"source": str(ids[i]), "target": str(ids[j]), "type": "related",
                          "provider": provider, "providers": [provider], "similarity": round(similarity, 6),
                          "provenance": [{"provider": provider, "method": "raw cosine",
                                          "observed_at": None, "ephemeral": True}]})
        # Complete-link merging prevents a similarity chain joining unrelated ends.
        groups = [{i} for i in range(len(prepared))]
        for _, i, j in candidates:
            left = next(group for group in groups if i in group)
            right = next(group for group in groups if j in group)
            if left is right:
                continue
            if min(similarities[a, b] for a in left for b in right) >= self.threshold:
                left.update(right)
                groups.remove(right)
        groups.sort(key=lambda group: (-len(group), min(ids[i] for i in group)))
        clusters = [{"label": str(prepared[min(group)]["title"]), "size": len(group),
                     "method": "embedding complete-link", "papers": [prepared[i] for i in sorted(group)]}
                    for group in groups]
        return {**metadata, "edges": edges, "clusters": clusters}
