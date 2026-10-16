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

    Load an existing local/cached model only when scoring is requested.
    Missing weights never trigger downloads; callers can fall back to keywords.
    """

    model_name: str = "all-MiniLM-L6-v2"
    batch_size: int = 32
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
            try:
                self._model = SentenceTransformer(
                    self.model_name, local_files_only=True, trust_remote_code=False,
                )
            except (OSError, ValueError) as exc:
                raise RuntimeError(
                    "Semantic model is not available locally. Provision it explicitly "
                    "and select its local path, or use keyword scoring (--no-semantic)."
                ) from exc
        return self._model

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        model = self._load()
        text_list = list(texts)
        if not text_list:
            return np.empty((0, 0), dtype=np.float32)
        embeddings = model.encode(
            text_list,
            batch_size=max(1, int(self.batch_size)),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
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
