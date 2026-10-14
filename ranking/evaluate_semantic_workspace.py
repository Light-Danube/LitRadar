"""Offline smoke evaluation: python -m ranking.evaluate_semantic_workspace --help."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import numpy as np

from .semantic_workspace import LocalSentenceTransformerEmbedder, SemanticWorkspace


class LexicalControl:
    """Title bag-of-words control; deliberately not a neural semantic model."""
    model_name = "lexical-control-not-neural"

    def encode(self, texts):
        tokens = [re.findall(r"[a-z]{3,}", text.casefold()) for text in texts]
        vocabulary = sorted({token for row in tokens for token in row})
        return np.asarray([[row.count(token) for token in vocabulary] for row in tokens], dtype=float)


def evaluate(papers, workspace):
    result = workspace.analyze(papers)
    expected = {(str(a["id"]), str(b["id"])) for i, a in enumerate(papers)
                for b in papers[i + 1:] if a["topic"] == b["topic"]}
    predicted = {(edge["source"], edge["target"]) for edge in result["edges"]}
    correct = len(expected & predicted)
    cluster_pairs = {tuple(sorted((str(a["id"]), str(b["id"]))))
                     for cluster in result["clusters"] for i, a in enumerate(cluster["papers"])
                     for b in cluster["papers"][i + 1:]}
    return {"model": result["model"], "threshold": result["threshold"], "papers": len(papers),
            "expected_pairs": len(expected), "predicted_pairs": len(predicted), "correct_pairs": correct,
            "edge_precision": correct / len(predicted) if predicted else None,
            "edge_recall": correct / len(expected) if expected else None,
            "cluster_pair_precision": len(cluster_pairs & expected) / len(cluster_pairs) if cluster_pairs else None,
            "cluster_pair_recall": len(cluster_pairs & expected) / len(expected) if expected else None,
            "note": "Six-title smoke corpus with author topic labels; not a general quality benchmark"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--local-model", type=Path)
    modes.add_argument("--lexical-control", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "tests/fixtures/semantic-public-titles.json")
    args = parser.parse_args()
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    embedder = LexicalControl() if args.lexical_control else LocalSentenceTransformerEmbedder(args.local_model)
    print(json.dumps(evaluate(corpus["papers"], SemanticWorkspace(embedder, threshold=args.threshold)), indent=2))


if __name__ == "__main__":
    main()
