from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


class TextEmbedder(Protocol):
    model_name: str

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return an array shaped (len(texts), embedding_dim)."""


@dataclass(slots=True)
class SentenceTransformerEmbedder:
    """Lazy wrapper around sentence-transformers.

    The model is loaded only when the embedder is instantiated, so importing
    LitRadar does not require the heavyweight dependency until v0.2 semantic
    scoring is actually requested.
    """

    model_name: str = "all-MiniLM-L6-v2"
    _model: object | None = None

    def _load(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "Semantic scoring requires sentence-transformers. "
                    "Install it with: python -m pip install -r requirements.txt"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        model = self._load()
        embeddings = model.encode(list(texts), normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)


def cosine_similarity_matrix(embeddings: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Return cosine similarity for each row against one query vector."""
    matrix = np.asarray(embeddings, dtype=np.float32)
    vector = np.asarray(query, dtype=np.float32).reshape(-1)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    vector_norm = float(np.linalg.norm(vector))
    if vector_norm == 0.0:
        return np.zeros(len(matrix), dtype=np.float32)
    denom = matrix_norms * vector_norm
    result = np.zeros(len(matrix), dtype=np.float32)
    mask = denom > 0
    result[mask] = (matrix[mask] @ vector) / denom[mask]
    return result


def cosine_to_unit_interval(values: np.ndarray) -> np.ndarray:
    """Map cosine similarity [-1, 1] into [0, 1]."""
    return np.clip((np.asarray(values, dtype=np.float32) + 1.0) / 2.0, 0.0, 1.0)
