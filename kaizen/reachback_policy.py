"""Policy for classifying raw-corpus reach-back during downstream PMM artifact generation.

Healthy reach-back: proof, examples, competitor detail, evidence recovery, appendix material.
Unhealthy reach-back: re-deriving core strategy (wedge, ICP, category, GTM choice, primary risks,
pain hierarchy, SAM) from the raw scenario corpus when the research brief should already carry it.
"""

from __future__ import annotations

import re
from enum import StrEnum


class ReachBackCategory(StrEnum):
    # --- Allowed enrichment (corpus OK as secondary source) ---
    proof = "proof"
    example = "example"
    competitor_detail = "competitor_detail"
    evidence_recovery = "evidence_recovery"
    appendix_support = "appendix_support"

    # --- Disallowed re-synthesis (should come from research brief) ---
    wedge_decision = "wedge_decision"
    icp_decision = "icp_decision"
    category_decision = "category_decision"
    gtm_motion_decision = "gtm_motion_decision"
    primary_risk_model = "primary_risk_model"
    primary_problem_framing = "primary_problem_framing"
    primary_market_structure = "primary_market_structure"


ALLOWED_REACHBACK_CATEGORIES: frozenset[ReachBackCategory] = frozenset(
    {
        ReachBackCategory.proof,
        ReachBackCategory.example,
        ReachBackCategory.competitor_detail,
        ReachBackCategory.evidence_recovery,
        ReachBackCategory.appendix_support,
    },
)

# Tier A: explicit “which bet” choices — worst class of inappropriate reach-back.
DISALLOWED_DECISION_CATEGORIES: frozenset[ReachBackCategory] = frozenset(
    {
        ReachBackCategory.wedge_decision,
        ReachBackCategory.icp_decision,
        ReachBackCategory.gtm_motion_decision,
    },
)

# Tier B: framing / hierarchy that the brief should preserve holistically.
DISALLOWED_FRAMING_CATEGORIES: frozenset[ReachBackCategory] = frozenset(
    {
        ReachBackCategory.category_decision,
        ReachBackCategory.primary_risk_model,
        ReachBackCategory.primary_problem_framing,
        ReachBackCategory.primary_market_structure,
    },
)

DISALLOWED_REACHBACK_CATEGORIES: frozenset[ReachBackCategory] = (
    DISALLOWED_DECISION_CATEGORIES | DISALLOWED_FRAMING_CATEGORIES
)


def is_allowed_reachback(category: ReachBackCategory) -> bool:
    return category in ALLOWED_REACHBACK_CATEGORIES


def is_disallowed_reachback(category: ReachBackCategory) -> bool:
    return category in DISALLOWED_REACHBACK_CATEGORIES


def classify_reach_back_query(description: str) -> ReachBackCategory | None:
    """
    Lightweight keyword classifier for operator / synthetic reach-back intents.

    Downstream stages should pass a short natural-language reason when touching the corpus.
    Returns None when the intent is ambiguous (callers may treat as review-needed).
    """
    low = (description or "").lower().strip()
    if not low:
        return None

    # Disallowed (check before allowed; more damaging misuses win).
    if re.search(
        r"\b(strategic wedge|wedge axis|why we win|positioning choice|competitive wedge)\b",
        low,
    ):
        return ReachBackCategory.wedge_decision
    if re.search(
        r"\b(icp|ideal customer|target segment|buyer archetype|persona selection|who we sell to)\b",
        low,
    ):
        return ReachBackCategory.icp_decision
    if re.search(
        r"\b(gtm motion|go-?to-?market motion|route to market|channel strategy choice|oem vs direct)\b",
        low,
    ):
        return ReachBackCategory.gtm_motion_decision
    if re.search(
        r"\b(category framing|category definition|how we categorize|market category)\b",
        low,
    ):
        return ReachBackCategory.category_decision
    if re.search(
        r"\b(primary risk|top risk|risk model|risk stack|main uncertainties)\b",
        low,
    ) and not re.search(r"\b(example|appendix|citation)\b", low):
        return ReachBackCategory.primary_risk_model
    if re.search(
        r"\b(pain hierarchy|rank pains|primary pain|top problem|problem stack|which pain first)\b",
        low,
    ):
        return ReachBackCategory.primary_problem_framing
    if re.search(
        r"\b(sam boundary|tam vs sam|addressable market|market structure|who is in scope)\b",
        low,
    ):
        return ReachBackCategory.primary_market_structure

    # Allowed enrichment (proof/competitor before generic "appendix" so "benchmark for appendix" → proof)
    if re.search(
        r"\b(exact quote|citation|verbatim|source line|page reference)\b",
        low,
    ):
        return ReachBackCategory.evidence_recovery
    if re.search(
        r"\b(benchmark number|benchmark\b|specific metric|proof point|audit trail|poc result|hard data)\b",
        low,
    ):
        return ReachBackCategory.proof
    if re.search(r"\b(for example|illustrative example|case example|customer story snippet)\b", low):
        return ReachBackCategory.example
    if re.search(
        r"\b(competitor sku|vendor sku|named competitor feature|specific product name|pricing tier)\b",
        low,
    ):
        return ReachBackCategory.competitor_detail
    if re.search(r"\b(appendix|supplemental|supporting detail|deep dive)\b", low):
        return ReachBackCategory.appendix_support

    return None
