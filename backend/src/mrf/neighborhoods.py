"""Neighborhood extraction and matching helpers."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from sqlalchemy.orm import Session

from mrf.db.models import Neighborhood

TITLE_NEIGHBORHOOD_RE = re.compile(r"\ben\s+([^,]+),\s*Madrid\.?$", re.IGNORECASE)
TRAILING_NEIGHBORHOOD_RE = re.compile(r"(?:en alquiler(?: en)?|alquiler(?: en)?|en)\s+([^,.]+?)(?:,\s*Madrid|\.?)$", re.IGNORECASE)


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    return text or None


def normalize_place_name(text: str | None) -> str:
    text = _clean(text) or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_neighborhood_from_title(title: str | None) -> str | None:
    title = _clean(title)
    if not title:
        return None

    candidate = None
    suffix_match = re.search(r",\s*Madrid\.?$", title, re.IGNORECASE)
    if suffix_match:
        prefix = title[:suffix_match.start()]
        lower_prefix = prefix.casefold()
        idx = lower_prefix.rfind(" en ")
        if idx != -1:
            candidate = _clean(prefix[idx + 4:])
        else:
            matches = list(TITLE_NEIGHBORHOOD_RE.finditer(title))
            if matches:
                candidate = _clean(matches[-1].group(1))

    if not candidate:
        m = re.search(r"\ben\s+Madrid\s*,\s*([^,.]+)$", title, re.IGNORECASE)
        if m:
            candidate = _clean(m.group(1))

    if not candidate:
        m = re.search(r"[,\-]\s*([^,.]+)\.?$", title)
        if m:
            tail = _clean(m.group(1))
            if tail and len(tail.split()) <= 4:
                candidate = tail

    if not candidate:
        lower_title = title.casefold()
        markers = [" en piso compartido en ", " habitaciones en ", " en "]
        for marker in markers:
            idx = lower_title.rfind(marker)
            if idx != -1:
                candidate = _clean(title[idx + len(marker):])
                break

    if not candidate:
        m = TRAILING_NEIGHBORHOOD_RE.search(title)
        if m:
            candidate = _clean(m.group(1))

    if not candidate:
        return None
    banned = {
        "madrid", "comunidad de madrid", "piso compartido", "apartamento", "habitacion",
        "habitación", "estudio", "piso", "casa", "chalet", "madrid capital",
    }
    if normalize_place_name(candidate) in {normalize_place_name(x) for x in banned}:
        return None
    return candidate


@lru_cache(maxsize=1)
def _load_neighborhood_index() -> dict[str, tuple[int, str, int | None]]:
    from mrf.db.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(Neighborhood).all()
        index: dict[str, tuple[int, str, int | None]] = {}
        for row in rows:
            key = normalize_place_name(row.name)
            if key:
                index[key] = (row.id, row.name, row.district_id)
        return index
    finally:
        db.close()


def match_neighborhood(db: Session, candidate: str | None) -> tuple[int | None, str | None, int | None]:
    del db  # signature kept for callers/scripts; cache loads via SessionLocal
    candidate = _clean(candidate)
    if not candidate:
        return None, None, None
    hit = _load_neighborhood_index().get(normalize_place_name(candidate))
    if not hit:
        return None, candidate, None
    neighborhood_id, canonical_name, district_id = hit
    return neighborhood_id, canonical_name, district_id


def apply_title_neighborhood_fallback(
    db: Session,
    *,
    title: str | None,
    neighborhood_raw: str | None,
    district_id: int | None,
) -> tuple[str | None, int | None, int | None]:
    current = _clean(neighborhood_raw)
    if current and normalize_place_name(current) not in {"", "madrid", "comunidad de madrid"}:
        return current, None, district_id

    extracted = extract_neighborhood_from_title(title)
    if not extracted:
        return current, None, district_id

    neighborhood_id, canonical_name, matched_district_id = match_neighborhood(db, extracted)
    return canonical_name or extracted, neighborhood_id, district_id or matched_district_id
