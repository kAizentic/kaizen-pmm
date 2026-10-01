"""
Deterministic provenance-aware composite adjustment from Signal.payload.source_provenance.

Does not alter the six PMM dimensions or coherence; only scales coherence-adjusted composite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _u01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x

_AUTHORITY_BY_SOURCE_TYPE: dict[str, float] = {
    "deep_research_report": 0.96,
    "manual_note": 0.88,
    "news_web": 0.78,
    "youtube": 0.58,
    "reddit": 0.48,
}

_AUTHOR_TYPE_DELTA: dict[str, float] = {
    "organization": 0.065,
    "individual": 0.02,
    "system": -0.11,
    "bot": -0.11,
    "unknown": 0.0,
}

# Sorted for deterministic iteration
_PROMOTIONAL_PHRASES: tuple[str, ...] = tuple(
    sorted(
        (
            "affiliate",
            "buy now",
            "click here",
            "discount code",
            "dm me",
            "limited time",
            "promo code",
            "sign up now",
            "sponsored",
            "use code",
        ),
    ),
)

_MULT_BASE = 0.82
_MULT_AUTH_COEF = 0.20
_MULT_QUAL_COEF = 0.08
_MULT_PEN_COEF = 0.32
_MULT_MIN = 0.70
_MULT_MAX = 1.08


def _authority_from_envelope(sp: dict[str, Any]) -> float:
    st = sp.get("source_type")
    st_key = st if isinstance(st, str) else ""
    base = _AUTHORITY_BY_SOURCE_TYPE.get(st_key, 0.62)
    at = sp.get("author_type")
    at_key = at.strip().lower() if isinstance(at, str) else "unknown"
    if at_key not in _AUTHOR_TYPE_DELTA:
        at_key = "unknown"
    return _u01(base + _AUTHOR_TYPE_DELTA[at_key])


def _quality_from_envelope(sp: dict[str, Any]) -> float:
    refs = sp.get("evidence_refs")
    url_n = 0
    cit_n = 0
    if isinstance(refs, list):
        for r in refs:
            if not isinstance(r, dict):
                continue
            rt = r.get("ref_type")
            if rt == "url":
                url_n += 1
            elif rt == "citation":
                cit_n += 1
    q = 0.48
    q += min(0.14, 0.045 * url_n)
    q += min(0.12, 0.06 * cit_n)
    ch = sp.get("channel_or_community")
    if isinstance(ch, str) and ch.strip():
        q += 0.06
    if sp.get("content_fingerprint"):
        q += 0.04
    plat = sp.get("source_platform")
    if isinstance(plat, str) and plat.strip() and plat.lower() not in ("unknown", "generic"):
        q += 0.02
    return _u01(q)


def _promotional_penalty(sp: dict[str, Any], promo_blob: str) -> float:
    low = promo_blob.lower()
    hits = sum(1 for p in _PROMOTIONAL_PHRASES if p in low)
    pen = min(0.52, 0.086 * hits)
    st = sp.get("source_type")
    if st == "reddit" and hits >= 2:
        pen = _u01(pen + 0.085)
    if st == "youtube" and hits >= 2:
        pen = _u01(pen + 0.05)
    return _u01(pen)


def _promotional_corpus(payload: dict[str, Any], sp: dict[str, Any]) -> str:
    parts: list[str] = []
    t = payload.get("text")
    if isinstance(t, str):
        parts.append(t)
    tit = sp.get("title")
    if isinstance(tit, str):
        parts.append(tit)
    try:
        parts.append(json.dumps(sp, sort_keys=True))
    except (TypeError, ValueError):
        parts.append(str(sp))
    return "\n".join(parts)


@dataclass(frozen=True)
class ProvenanceLayerResult:
    """When applied=False, multiplier is 1.0 and composite should stay unchanged."""

    applied: bool
    source_authority_score: float | None
    source_signal_quality_score: float | None
    promotional_risk_penalty: float | None
    provenance_composite_multiplier: float
    provenance_adjustment_reason: str | None


def evaluate_provenance_layer(payload: dict[str, Any]) -> ProvenanceLayerResult:
    """
    Read ``payload['source_provenance']`` if it is a non-empty dict.

    Returns multiplier in [_MULT_MIN, _MULT_MAX] when applied; otherwise 1.0 and NULL-able scores.
    """
    raw = payload.get("source_provenance")
    if not isinstance(raw, dict) or len(raw) == 0:
        return ProvenanceLayerResult(
            applied=False,
            source_authority_score=None,
            source_signal_quality_score=None,
            promotional_risk_penalty=None,
            provenance_composite_multiplier=1.0,
            provenance_adjustment_reason=None,
        )

    sp = raw
    authority = _authority_from_envelope(sp)
    quality = _quality_from_envelope(sp)
    blob = _promotional_corpus(payload, sp)
    penalty = _promotional_penalty(sp, blob)

    mult = (
        _MULT_BASE
        + _MULT_AUTH_COEF * authority
        + _MULT_QUAL_COEF * quality
        - _MULT_PEN_COEF * penalty
    )
    mult = max(_MULT_MIN, min(_MULT_MAX, mult))

    st = sp.get("source_type")
    st_s = st if isinstance(st, str) else "?"
    reason = (
        f"provenance:mult={mult:.4f};authority={authority:.3f};quality={quality:.3f};"
        f"penalty={penalty:.3f};source_type={st_s}"
    )

    return ProvenanceLayerResult(
        applied=True,
        source_authority_score=authority,
        source_signal_quality_score=quality,
        promotional_risk_penalty=penalty,
        provenance_composite_multiplier=mult,
        provenance_adjustment_reason=reason,
    )
