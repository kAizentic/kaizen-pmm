"""Tier assignment and promotion eligibility (explicit Opportunity promotion via API)."""

from __future__ import annotations

from typing import Literal

PriorityTier = Literal["P0", "P1", "P2", "P3"]

_TIERS: tuple[PriorityTier, ...] = ("P0", "P1", "P2", "P3")

_COHERENCE_TIER_CAP = 0.75


def _rank(tier: PriorityTier) -> int:
    return _TIERS.index(tier)


def _tier_from_rank(rank: int) -> PriorityTier:
    rank = max(0, min(3, rank))
    return _TIERS[rank]


def assign_priority_tier(
    composite_score: float,
    *,
    problem_clarity_score: float,
    buyer_salience_score: float,
    commercial_impact_score: float,
    differentiation_opening_score: float,
    evidence_strength_score: float,
    actionability_now_score: float,
    coherence_score: float,
) -> PriorityTier:
    """
    P0–P3 from coherence-adjusted composite, then PMM gates.

    Gates: (1) thin problem+evidence, (2) weak problem→buyer→impact→evidence chain.
    """
    if composite_score >= 0.80:
        rank = _rank("P0")
    elif composite_score >= 0.62:
        rank = _rank("P1")
    elif composite_score >= 0.38:
        rank = _rank("P2")
    else:
        rank = _rank("P3")

    if problem_clarity_score < 0.25 and evidence_strength_score < 0.15:
        if rank < _rank("P2"):
            rank = _rank("P2")

    if coherence_score < _COHERENCE_TIER_CAP:
        if rank < _rank("P2"):
            rank = _rank("P2")

    return _tier_from_rank(rank)


def is_promotion_eligible(tier: PriorityTier | str) -> bool:
    """True when tier is suitable for later Opportunity promotion (operator workflow)."""
    return tier in ("P0", "P1")


def meets_promotion_threshold(composite_score: float, *, minimum: float) -> bool:
    """Return True if ``composite_score`` is at or above ``minimum`` (legacy composite check)."""
    return composite_score >= minimum


def build_promotion_blockers(
    priority_tier: str,
    *,
    composite_score: float,
    coherence_score: float,
    problem_clarity_score: float,
    evidence_strength_score: float,
) -> list[str]:
    """
    Human-readable reasons the latest score is not promotion-eligible (P0/P1).

    Uses the same thresholds as assign_priority_tier; ordering is deterministic.
    """
    if priority_tier in ("P0", "P1"):
        return []
    out: list[str] = []
    if composite_score < 0.62:
        out.append(
            f"adjusted_composite {composite_score:.4f} is below P1 threshold 0.62",
        )
    if coherence_score < 0.75:
        out.append(
            f"coherence_score {coherence_score:.4f} is below 0.75 (strict); "
            "P0/P1 require coherence at or above 0.75 (all chain dimensions >= 0.22)",
        )
    if problem_clarity_score < 0.25 and evidence_strength_score < 0.15:
        out.append(
            "problem_clarity_score < 0.25 and evidence_strength_score < 0.15 "
            "(thin problem+evidence gate caps tier at P2)",
        )
    return out
