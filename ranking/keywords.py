from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KeywordGroup:
    name: str
    weight: float
    terms: tuple[str, ...]


class KeywordProfile:
    def __init__(
        self,
        groups: list[KeywordGroup],
        name: str = "Unnamed profile",
        description: str = "",
        keyword_weight: float = 0.35,
        semantic_weight: float = 0.65,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.groups = groups
        self.name = name
        self.description = description
        self.keyword_weight = float(keyword_weight)
        self.semantic_weight = float(semantic_weight)
        self.embedding_model = embedding_model
        total = self.keyword_weight + self.semantic_weight
        if total <= 0:
            raise ValueError("keyword_weight + semantic_weight must be positive")
        self.keyword_weight /= total
        self.semantic_weight /= total

    @classmethod
    def from_json(cls, path: str | Path) -> "KeywordProfile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        ranking = data.get("ranking", {})
        groups = [
            KeywordGroup(
                name=str(g["name"]),
                weight=float(g["weight"]),
                terms=tuple(str(t) for t in g.get("terms", [])),
            )
            for g in data.get("groups", [])
        ]
        return cls(
            groups=groups,
            name=str(data.get("name", "Unnamed profile")),
            description=str(data.get("description", "")),
            keyword_weight=float(ranking.get("keyword_weight", 0.35)),
            semantic_weight=float(ranking.get("semantic_weight", 0.65)),
            embedding_model=str(ranking.get("embedding_model", "all-MiniLM-L6-v2")),
        )

    def match(self, text: str) -> dict[str, list[str]]:
        normalized = _normalize(text)
        hits: dict[str, list[str]] = {}
        for group in self.groups:
            matched: list[str] = []
            for term in group.terms:
                if _term_present(normalized, _normalize(term)):
                    matched.append(term)
            if matched:
                hits[group.name] = matched
        return hits

    def as_embedding_text(self) -> str:
        group_text = "; ".join(
            f"{group.name}: {', '.join(group.terms)}" for group in self.groups
        )
        return " | ".join(part for part in [self.description, group_text] if part)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _term_present(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None
