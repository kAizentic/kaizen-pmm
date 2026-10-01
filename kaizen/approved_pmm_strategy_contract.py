"""
Approved PMM strategy: compact decision object for decision-record-first downstream generation.

Built only from ResearchDecisionRecord + eligible canonical assertions (+ approved contrasts/proofs).
Downstream collateral should prefer this over raw research brief section prose.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from kaizen.artifact_quality_contract import MessagingBriefQualityReport
from kaizen.cross_artifact_consistency_contract import CrossArtifactConsistencyReport
from kaizen.canonical_assertion_contract import ApprovedCompetitiveContrast

APPROVED_PMM_STRATEGY_CONTRACT_VERSION: Final[str] = "1.2"


class ApprovalStatus(StrEnum):
    approved = "approved"
    pending_gaps = "pending_gaps"
    blocked = "blocked"


class FieldSelectionTrace(BaseModel):
    """Observability for one chosen strategy line or list item."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    why_selected: str = Field(default="", max_length=2400)
    why_rejected_top_alternative: str | None = Field(default=None, max_length=2400)
    source_ids: list[str] = Field(default_factory=list)
    quality_score_breakdown: dict[str, float] = Field(default_factory=dict)


class ApprovedPMMStrategyCoherenceReport(BaseModel):
    """Cross-field coherence evaluation for ApprovedPMMStrategy (observability + rerank signal)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    overall_coherence_score: float = Field(..., ge=0.0, le=1.0)
    wedge_positioning_alignment: float = Field(..., ge=0.0, le=1.0)
    wedge_proof_alignment: float = Field(..., ge=0.0, le=1.0)
    wedge_metric_alignment: float = Field(..., ge=0.0, le=1.0)
    icp_pain_alignment: float = Field(..., ge=0.0, le=1.0)
    icp_gtm_alignment: float = Field(..., ge=0.0, le=1.0)
    proof_metric_alignment: float = Field(..., ge=0.0, le=1.0)
    contrast_positioning_alignment: float = Field(..., ge=0.0, le=1.0)
    contrast_proof_alignment: float = Field(..., ge=0.0, le=1.0)
    narrative_focus_score: float = Field(..., ge=0.0, le=1.0)
    contradiction_flags: list[str] = Field(default_factory=list)
    redundancy_flags: list[str] = Field(default_factory=list)
    missing_link_flags: list[str] = Field(default_factory=list)
    coherence_summary: str = Field(default="", max_length=2400)
    improvement_suggestions: list[str] = Field(default_factory=list)
    field_pair_notes: dict[str, str] = Field(default_factory=dict)


class ApprovedPMMStrategySelectionProvenance(BaseModel):
    """Traces for senior-PMM selection / compression layer (parallel to strategy field values)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    strategic_wedge: FieldSelectionTrace | None = None
    positioning_frame: FieldSelectionTrace | None = None
    category_frame: FieldSelectionTrace | None = None
    icp_primary: FieldSelectionTrace | None = None
    gtm_motion: FieldSelectionTrace | None = None
    top_pain_points: list[FieldSelectionTrace] = Field(default_factory=list)
    proof_points: list[FieldSelectionTrace] = Field(default_factory=list)
    competitive_contrasts: list[FieldSelectionTrace] = Field(default_factory=list)
    key_metrics: list[FieldSelectionTrace] = Field(default_factory=list)


class ApprovedPMMStrategy(BaseModel):
    """Explicit approved decisions and derived messaging inputs for downstream assets."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=APPROVED_PMM_STRATEGY_CONTRACT_VERSION, max_length=16)
    strategic_wedge: str = Field(..., min_length=4, max_length=1200)
    positioning_frame: str = Field(..., min_length=4, max_length=1200)
    category_frame: str = Field(..., min_length=4, max_length=1200)
    icp_primary: str = Field(..., min_length=4, max_length=800)
    icp_secondary_optional: list[str] = Field(default_factory=list)
    top_pain_points: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    competitive_contrasts: list[ApprovedCompetitiveContrast] = Field(default_factory=list)
    gtm_motion: str = Field(..., min_length=4, max_length=1200)
    key_metrics: list[str] = Field(default_factory=list)
    buyer_language_terms: list[str] = Field(default_factory=list)
    banned_internal_terms: list[str] = Field(
        default_factory=list,
        description="Terms that must not appear in external buyer copy.",
    )
    unresolved_gaps: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = Field(default=ApprovalStatus.pending_gaps)
    selection_provenance: ApprovedPMMStrategySelectionProvenance | None = Field(
        default=None,
        description="Ranking/dedup trace for operator QA; optional for legacy stored rows.",
    )
    coherence_report: ApprovedPMMStrategyCoherenceReport | None = Field(
        default=None,
        description="Cross-field narrative coherence; optional for legacy stored rows.",
    )


class OnePagerAssetShapeContract(BaseModel):
    """Required narrative slots for a buyer-facing one-pager (decision-first)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    headline: str = Field(..., min_length=8, max_length=400)
    subhead: str = Field(..., min_length=6, max_length=400)
    problem: str = Field(..., min_length=12, max_length=2000)
    why_now: str = Field(..., min_length=12, max_length=2000)
    proof: list[str] = Field(..., min_length=1, max_length=5)
    differentiation: list[str] = Field(..., min_length=1, max_length=8)
    cta: str = Field(..., min_length=12, max_length=1200)


class ChannelPlanAssetShapeContract(BaseModel):
    """Structured channel / launch row shape (decision-first)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    motion: str = Field(..., min_length=8, max_length=800)
    audience: str = Field(..., min_length=4, max_length=600)
    why_this_channel: str = Field(..., min_length=12, max_length=1200)
    asset_types: list[str] = Field(default_factory=list)
    proof_needed: str = Field(..., min_length=8, max_length=1500)
    kpi: str = Field(..., min_length=6, max_length=600)
    next_action: str = Field(..., min_length=8, max_length=800)


class MessagingBriefAssetShapeContract(BaseModel):
    """Messaging brief slots aligned to approved strategy (no raw research paste)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category_frame: str = Field(..., min_length=8, max_length=800)
    positioning: str = Field(..., min_length=8, max_length=1200)
    icp: str = Field(..., min_length=8, max_length=800)
    pains: list[str] = Field(..., min_length=1, max_length=12)
    proof_points: list[str] = Field(..., min_length=1, max_length=12)
    differentiation: list[str] = Field(..., min_length=1, max_length=8)
    talk_track: str = Field(..., min_length=20, max_length=2500)
    quality_report: MessagingBriefQualityReport | None = Field(
        default=None,
        description="Artifact-level messaging brief QA.",
    )
    rewrite_applied: bool = Field(default=False)
    rewrite_reason: str | None = Field(default=None, max_length=800)
    cross_artifact_consistency_report: CrossArtifactConsistencyReport | None = Field(
        default=None,
        description="Cross-artifact consistency when evaluated with peer payloads.",
    )
    cross_artifact_normalization_applied: bool = Field(default=False)
    cross_artifact_normalization_reason: str | None = Field(default=None, max_length=1600)


def validate_approved_pmm_strategy_dict(data: dict[str, object]) -> ApprovedPMMStrategy:
    return ApprovedPMMStrategy.model_validate(data)
