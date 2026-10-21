"""Explicit provider metadata-language semantics, never full-text language."""
from __future__ import annotations

# ISO 639-1 codes used by OpenAlex's vocabulary. Membership identifies a
# provider metadata value; it is not independent language determination.
ISO_639_1 = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr
cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu
gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk
kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms
mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro
ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl
tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu
""".split())


def normalize_metadata_language(value: str) -> str:
    if not isinstance(value, str) or value.strip().casefold() not in {"any", "uk", "en"}:
        raise ValueError("Metadata language must be any, uk or en")
    return value.strip().casefold()


def metadata_language_value(raw: object) -> str | None:
    # Raw values stay preserved; never infer language from script or country.
    return raw.casefold() if isinstance(raw, str) and raw.casefold() in ISO_639_1 else None


def paper_from_cache(item: dict):
    """Reconstruct language provenance from raw data in pre-feature caches."""
    from .base import Paper
    paper = Paper(**item)
    if paper.source == "openalex":
        raw = paper.raw if isinstance(paper.raw, dict) else {}
        paper.metadata_language = metadata_language_value(raw.get("language"))
        paper.language_basis = "openalex_detected_title_abstract"
    return paper
