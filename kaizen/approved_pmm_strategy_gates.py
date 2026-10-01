"""
Hard gates and buyer-language rules for decision-record-first downstream generation.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from kaizen.approved_pmm_strategy_contract import (
    ApprovalStatus,
    ApprovedPMMStrategy,
    ChannelPlanAssetShapeContract,
    MessagingBriefAssetShapeContract,
    OnePagerAssetShapeContract,
)
from kaizen.channel_execution_contract import ChannelExecutionFrameworkError, ChannelExecutionStructuredPayload
from kaizen.collateral_contract import CollateralFrameworkError

ArtifactExposure = Literal["external_buyer", "internal_strategy"]

# Abstract / internal phrasing prohibited in external buyer assets (extend downstream_synthesis list).
_PROHIBITED_BUYER_ABSTRACT_PHRASES: tuple[str, ...] = (
    "evidence posture",
    "insight priority",
    "strategic resolution levers",
    "conflicts with other personas",
    "research brief for scenario",
    "pmm critique",
    "serialized evidence",
)

# Outcome signals: at least one should appear in headline + problem + proof blob for buyer assets.
_OUTCOME_SIGNAL = re.compile(
    r"\d[\d,]*%|\$[\d,]+|[\d,]+\s*(?:m|b|k|million|billion|hours?|minutes?|days?)\b|"
    r"\broi\b|\btco\b|\blatency\b|\buptime\b|\bdowntime\b|\bcost\b|\brevenue\b|\bdeploy\b|\brollout\b|"
    r"\bthroughput\b|\bbudget\b|\brenewal\b|\bprocurement\b|\bbenchmark\b|\bpoc\b|\boutage\b",
    re.I,
)


def parse_approved_pmm_strategy_from_evidence_table(
    evidence_table: list[Any] | dict[str, Any] | None,
) -> ApprovedPMMStrategy | None:
    if not isinstance(evidence_table, list):
        return None
    for row in evidence_table:
        if isinstance(row, dict) and row.get("kind") == "approved_pmm_strategy":
            try:
                return ApprovedPMMStrategy.model_validate({k: v for k, v in row.items() if k != "kind"})
            except Exception:
                return None
    return None


_SCRUB_TERMS: tuple[str, ...] = tuple(
    dict.fromkeys(
        [
            *_PROHIBITED_BUYER_ABSTRACT_PHRASES,
            "pmm critique",
            "critique quality",
            "research brief for scenario",
            "derived heuristics only",
            "serialized evidence",
            "content_fingerprint",
        ],
    ),
)


def scrub_buyer_prohibited_phrases(text: str) -> str:
    """Remove internal/abstract banned phrases from legacy-composed strings (best-effort hygiene)."""
    t = text or ""
    for p in _SCRUB_TERMS:
        t = re.sub(re.escape(p), "", t, flags=re.I)
    return " ".join(t.split())


def buyer_facing_strategy_violations(text: str, *, exposure: ArtifactExposure) -> list[str]:
    if exposure != "external_buyer":
        return []
    low = (text or "").lower()
    return [p for p in _PROHIBITED_BUYER_ABSTRACT_PHRASES if p in low]


def concrete_outcome_present(headline: str, problem: str, proof_lines: list[str]) -> bool:
    blob = " ".join([headline or "", problem or "", " ".join(proof_lines or [])])
    return bool(_OUTCOME_SIGNAL.search(blob))


def collect_one_pager_gaps(pmm: ApprovedPMMStrategy) -> list[str]:
    """Hard requirements before generating a full buyer one-pager from ApprovedPMMStrategy."""
    gaps: list[str] = []
    if pmm.approval_status == ApprovalStatus.blocked:
        gaps.append("approval_blocked")
    if pmm.approval_status == ApprovalStatus.pending_gaps:
        gaps.append("approval_status_pending_gaps")
    gaps.extend(pmm.unresolved_gaps)
    if len((pmm.strategic_wedge or "").strip()) < 8:
        gaps.append("strategic_wedge")
    if len((pmm.positioning_frame or "").strip()) < 8:
        gaps.append("positioning_frame")
    if len((pmm.icp_primary or "").strip()) < 8:
        gaps.append("icp_primary")
    substantive = [p for p in pmm.proof_points if len(p.strip()) >= 16]
    if len(substantive) < 2:
        gaps.append("proof_points_min_2")
    if not pmm.competitive_contrasts:
        gaps.append("competitive_contrast_min_1")
    if len((pmm.gtm_motion or "").strip()) < 12:
        gaps.append("gtm_motion")
    return sorted(set(gaps))


def collect_channel_launch_gaps(pmm: ApprovedPMMStrategy) -> list[str]:
    """Channel / launch outputs require an explicit committed GTM motion."""
    gaps: list[str] = []
    if len((pmm.gtm_motion or "").strip()) < 12:
        gaps.append("gtm_motion_required_for_channel")
    if pmm.approval_status == ApprovalStatus.blocked:
        gaps.append("approval_blocked")
    return sorted(set(gaps))


def raise_if_one_pager_gaps(pmm: ApprovedPMMStrategy) -> None:
    gaps = collect_one_pager_gaps(pmm)
    if gaps:
        raise CollateralFrameworkError(
            422,
            json.dumps(
                {
                    "error": "downstream_gate",
                    "artifact": "one_pager",
                    "gaps": gaps,
                    "message": "One-pager generation blocked until approved PMM strategy satisfies required decisions.",
                },
            ),
        )


def raise_if_channel_gaps(pmm: ApprovedPMMStrategy) -> None:
    gaps = collect_channel_launch_gaps(pmm)
    if gaps:
        raise ChannelExecutionFrameworkError(
            422,
            json.dumps(
                {
                    "error": "downstream_gate",
                    "artifact": "channel_execution",
                    "gaps": gaps,
                    "message": "Channel plan generation blocked until GTM motion is committed on ApprovedPMMStrategy.",
                },
            ),
        )


def assert_buyer_shape_language(
    shape: OnePagerAssetShapeContract | MessagingBriefAssetShapeContract,
    *,
    exposure: ArtifactExposure,
) -> None:
    if exposure != "external_buyer":
        return
    parts: list[str] = []
    if isinstance(shape, OnePagerAssetShapeContract):
        parts = [shape.headline, shape.subhead, shape.problem, shape.why_now, shape.cta, *shape.proof, *shape.differentiation]
    else:
        parts = [
            shape.category_frame,
            shape.positioning,
            shape.icp,
            shape.talk_track,
            *shape.pains,
            *shape.proof_points,
            *shape.differentiation,
        ]
    blob = " ".join(parts)
    bad = buyer_facing_strategy_violations(blob, exposure=exposure)
    if bad:
        raise ValueError(f"buyer-facing asset contains prohibited phrasing: {bad!r}")
    if isinstance(shape, OnePagerAssetShapeContract):
        if not concrete_outcome_present(shape.headline, shape.problem, shape.proof):
            raise ValueError(
                "buyer-facing one-pager requires at least one concrete operational/business outcome signal "
                "in headline, problem, or proof slots",
            )


def channel_gtm_matches_pmm(channel_motion_text: str, pmm: ApprovedPMMStrategy) -> bool:
    """Channel row must not invent a GTM motion absent from ApprovedPMMStrategy."""
    g = (pmm.gtm_motion or "").lower().strip()
    c = (channel_motion_text or "").lower().strip()
    if not g or not c:
        return False
    if g in c or c in g:
        return True
    g_tokens = {t for t in re.split(r"\W+", g) if len(t) >= 4}
    c_tokens = {t for t in re.split(r"\W+", c) if len(t) >= 4}
    if g_tokens & c_tokens:
        return True
    return False


def validate_channel_row_against_pmm(entry: ChannelPlanAssetShapeContract, pmm: ApprovedPMMStrategy) -> None:
    if not channel_gtm_matches_pmm(entry.motion, pmm):
        raise ChannelExecutionFrameworkError(
            422,
            json.dumps(
                {
                    "error": "gtm_motion_mismatch",
                    "message": "Channel motion must align with ApprovedPMMStrategy.gtm_motion; no invented GTM.",
                },
            ),
        )


def validate_channel_execution_payload_rows_against_pmm(
    payload: ChannelExecutionStructuredPayload,
    pmm: ApprovedPMMStrategy,
) -> None:
    """Re-run channel row GTM alignment for every prioritized channel row."""
    for ch in payload.prioritized_channels:
        deps = ch.dependencies or []
        next_act = (deps[0] if deps else "Review channel proof pack against ICP")[:800]
        validate_channel_row_against_pmm(
            ChannelPlanAssetShapeContract(
                motion=ch.objective,
                audience=ch.target_persona,
                why_this_channel=ch.message_emphasis,
                asset_types=ch.key_assets,
                proof_needed=ch.proof_needed,
                kpi=ch.success_signal,
                next_action=next_act,
            ),
            pmm,
        )
