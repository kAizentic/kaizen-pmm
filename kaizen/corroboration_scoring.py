"""
Deterministic cross-signal corroboration: similar text, time window, source diversity, polarity guard.

Applied after provenance; scales composite via a bounded multiplier. No external APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from kaizen.signal import Signal

_CORROB_WINDOW = timedelta(days=45)
_JACCARD_MIN = 0.28
_MULT_MIN = 1.0
_MULT_MAX = 1.10

_DECLINE_LEX: frozenset[str] = frozenset(
    {
        "churn",
        "decline",
        "decrease",
        "drop",
        "down",
        "fell",
        "loss",
        "lost",
        "failed",
        "worse",
    },
)
_GROWTH_LEX: frozenset[str] = frozenset(
    {
        "growth",
        "increase",
        "expansion",
        "up",
        "rose",
        "gain",
        "won",
        "better",
        "improved",
    },
)

_STOPWORDS: frozenset[str] = frozenset(
    sorted(
        {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "two",
            "who",
            "way",
            "use",
            "any",
            "had",
            "this",
            "that",
            "with",
            "from",
            "have",
            "been",
            "were",
            "they",
            "will",
            "what",
            "when",
            "than",
            "then",
            "into",
            "also",
            "only",
            "some",
            "such",
            "very",
            "just",
            "more",
            "most",
            "much",
            "many",
        },
    ),
)


def _dt_utc_epoch(dt: datetime) -> float:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).timestamp()
    return dt.timestamp()


def _combined_text(sig: Signal) -> str:
    p = sig.payload if isinstance(sig.payload, dict) else {}
    parts: list[str] = []
    sp = p.get("source_provenance")
    if isinstance(sp, dict):
        tit = sp.get("title")
        if isinstance(tit, str):
            parts.append(tit)
    t = p.get("text")
    if isinstance(t, str):
        parts.append(t)
    return "\n".join(parts).lower()


def _tokenize(sig: Signal) -> frozenset[str]:
    raw = _combined_text(sig)
    toks = re.findall(r"[a-z0-9]{3,}", raw)
    return frozenset(t for t in toks if t not in _STOPWORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union if union else 0.0


def _polarity_conflict(ta: frozenset[str], tb: frozenset[str]) -> bool:
    da = bool(ta & _DECLINE_LEX)
    ga = bool(ta & _GROWTH_LEX)
    db = bool(tb & _DECLINE_LEX)
    gb = bool(tb & _GROWTH_LEX)
    return (da and gb) or (ga and db)


def _source_identity(sig: Signal) -> tuple[str, str]:
    p = sig.payload if isinstance(sig.payload, dict) else {}
    sp = p.get("source_provenance")
    if isinstance(sp, dict):
        st = sp.get("source_type")
        plat = sp.get("source_platform")
        s = str(st).strip() if isinstance(st, str) else ""
        pl = str(plat).strip() if isinstance(plat, str) else ""
        if s or pl:
            return (s or "_", pl[:120] or "_")
    src = (sig.source or "").strip()[:120] or "unknown"
    return ("_", src)


def _within_window(a: datetime | None, b: datetime | None) -> bool:
    if a is None or b is None:
        return False
    return abs(_dt_utc_epoch(a) - _dt_utc_epoch(b)) <= _CORROB_WINDOW.total_seconds()


@dataclass(frozen=True)
class CorroborationResult:
    """Peer context absent → multiplier 1.0, score 0, short reason."""

    corroboration_score: float
    corroboration_composite_multiplier: float
    corroboration_peer_count: int
    corroboration_distinct_sources: int
    corroboration_source_summary: str
    corroboration_adjustment_reason: str


def evaluate_corroboration(
    signal: Signal,
    peer_signals: Sequence[Signal] | None,
) -> CorroborationResult:
    """
    Find peers with similar token sets, same time window, no polarity conflict,
    then require ≥2 distinct (source_type, source_platform) identities among
    {signal} ∪ corroborating peers.
    """
    if not peer_signals:
        return CorroborationResult(
            corroboration_score=0.0,
            corroboration_composite_multiplier=1.0,
            corroboration_peer_count=0,
            corroboration_distinct_sources=0,
            corroboration_source_summary="",
            corroboration_adjustment_reason="corroboration:no_peer_context",
        )

    toks_self = _tokenize(signal)
    if len(toks_self) < 5:
        return CorroborationResult(
            corroboration_score=0.0,
            corroboration_composite_multiplier=1.0,
            corroboration_peer_count=0,
            corroboration_distinct_sources=0,
            corroboration_source_summary="",
            corroboration_adjustment_reason="corroboration:sparse_text_skipped",
        )

    id_self = _source_identity(signal)
    candidates: list[Signal] = []
    for peer in peer_signals:
        if peer.id == signal.id:
            continue
        if not _within_window(signal.created_at, peer.created_at):
            continue
        toks_p = _tokenize(peer)
        if len(toks_p) < 5:
            continue
        if _jaccard(toks_self, toks_p) < _JACCARD_MIN:
            continue
        if _polarity_conflict(toks_self, toks_p):
            continue
        candidates.append(peer)

    identities: set[tuple[str, str]] = {id_self}
    for p in candidates:
        identities.add(_source_identity(p))

    if len(identities) < 2:
        return CorroborationResult(
            corroboration_score=0.0,
            corroboration_composite_multiplier=1.0,
            corroboration_peer_count=len(candidates),
            corroboration_distinct_sources=len(identities),
            corroboration_source_summary="|".join(sorted(f"{a}:{b}" for a, b in identities)),
            corroboration_adjustment_reason=(
                "corroboration:insufficient_cross_source_diversity"
                if candidates
                else "corroboration:no_similar_peers_in_window"
            ),
        )

    n = len(candidates)
    d = len(identities)
    # Normalized score in [0, 1]: cap contribution from count and diversity
    score = min(1.0, 0.22 * min(n, 5) + 0.12 * min(max(d - 2, 0), 4))
    mult = 1.0 + min(_MULT_MAX - _MULT_MIN, 0.018 * min(n, 6) + 0.014 * min(max(d - 2, 0), 5))
    mult = max(_MULT_MIN, min(_MULT_MAX, mult))

    summary_parts = sorted({f"{a}:{b}" for a, b in identities})
    summary = "|".join(summary_parts[:12])
    if len(summary_parts) > 12:
        summary += "|..."

    reason = (
        f"corroboration:peers={n};distinct_sources={d};score={score:.3f};mult={mult:.4f};"
        f"ids={summary}"
    )

    return CorroborationResult(
        corroboration_score=score,
        corroboration_composite_multiplier=mult,
        corroboration_peer_count=n,
        corroboration_distinct_sources=d,
        corroboration_source_summary=summary,
        corroboration_adjustment_reason=reason,
    )

