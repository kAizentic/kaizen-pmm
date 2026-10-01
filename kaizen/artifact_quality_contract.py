"""
Quality reports for downstream PMM artifacts (one-pager, channel plan row, messaging brief shape).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

ARTIFACT_QUALITY_CONTRACT_VERSION: Final[str] = "1.0"


class ArtifactQualityPassStatus(StrEnum):
    pass_ok = "pass"
    pass_after_rewrite = "pass_after_rewrite"
    fail = "fail"
    fail_after_rewrite = "fail_after_rewrite"


class OnePagerQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=ARTIFACT_QUALITY_CONTRACT_VERSION, max_length=16)
    overall_quality_score: float = Field(..., ge=0.0, le=1.0)
    compression_score: float = Field(..., ge=0.0, le=1.0)
    buyer_legibility_score: float = Field(..., ge=0.0, le=1.0)
    differentiation_score: float = Field(..., ge=0.0, le=1.0)
    proof_density_score: float = Field(..., ge=0.0, le=1.0)
    format_fitness_score: float = Field(..., ge=0.0, le=1.0)
    commercial_clarity_score: float = Field(..., ge=0.0, le=1.0)
    research_leakage_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0=clean, 1=heavy research-summary or meta phrasing.",
    )
    redundancy_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0=no cross-section redundancy, 1=high repetition.",
    )
    headline_strength: float = Field(..., ge=0.0, le=1.0)
    problem_clarity: float = Field(..., ge=0.0, le=1.0)
    why_now_strength: float = Field(..., ge=0.0, le=1.0)
    proof_strength: float = Field(..., ge=0.0, le=1.0)
    differentiation_strength: float = Field(..., ge=0.0, le=1.0)
    cta_strength: float = Field(..., ge=0.0, le=1.0)
    weaknesses: list[str] = Field(default_factory=list)
    rewrite_recommendations: list[str] = Field(default_factory=list)
    pass_status: ArtifactQualityPassStatus = Field(default=ArtifactQualityPassStatus.fail)


class ChannelPlanQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=ARTIFACT_QUALITY_CONTRACT_VERSION, max_length=16)
    overall_quality_score: float = Field(..., ge=0.0, le=1.0)
    compression_score: float = Field(..., ge=0.0, le=1.0)
    buyer_legibility_score: float = Field(..., ge=0.0, le=1.0)
    differentiation_score: float = Field(..., ge=0.0, le=1.0)
    proof_density_score: float = Field(..., ge=0.0, le=1.0)
    format_fitness_score: float = Field(..., ge=0.0, le=1.0)
    commercial_clarity_score: float = Field(..., ge=0.0, le=1.0)
    research_leakage_score: float = Field(..., ge=0.0, le=1.0)
    redundancy_score: float = Field(..., ge=0.0, le=1.0)
    motion_clarity: float = Field(..., ge=0.0, le=1.0)
    audience_fit: float = Field(..., ge=0.0, le=1.0)
    channel_rationale_strength: float = Field(..., ge=0.0, le=1.0)
    asset_actionability: float = Field(..., ge=0.0, le=1.0)
    proof_requirement_quality: float = Field(..., ge=0.0, le=1.0)
    kpi_quality: float = Field(..., ge=0.0, le=1.0)
    next_action_quality: float = Field(..., ge=0.0, le=1.0)
    weaknesses: list[str] = Field(default_factory=list)
    rewrite_recommendations: list[str] = Field(default_factory=list)
    pass_status: ArtifactQualityPassStatus = Field(default=ArtifactQualityPassStatus.fail)


class MessagingBriefQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=ARTIFACT_QUALITY_CONTRACT_VERSION, max_length=16)
    overall_quality_score: float = Field(..., ge=0.0, le=1.0)
    compression_score: float = Field(..., ge=0.0, le=1.0)
    buyer_legibility_score: float = Field(..., ge=0.0, le=1.0)
    differentiation_score: float = Field(..., ge=0.0, le=1.0)
    proof_density_score: float = Field(..., ge=0.0, le=1.0)
    format_fitness_score: float = Field(..., ge=0.0, le=1.0)
    commercial_clarity_score: float = Field(..., ge=0.0, le=1.0)
    research_leakage_score: float = Field(..., ge=0.0, le=1.0)
    redundancy_score: float = Field(..., ge=0.0, le=1.0)
    positioning_clarity: float = Field(..., ge=0.0, le=1.0)
    icp_specificity: float = Field(..., ge=0.0, le=1.0)
    pain_quality: float = Field(..., ge=0.0, le=1.0)
    proof_quality: float = Field(..., ge=0.0, le=1.0)
    contrast_quality: float = Field(..., ge=0.0, le=1.0)
    talk_track_strength: float = Field(..., ge=0.0, le=1.0)
    weaknesses: list[str] = Field(default_factory=list)
    rewrite_recommendations: list[str] = Field(default_factory=list)
    pass_status: ArtifactQualityPassStatus = Field(default=ArtifactQualityPassStatus.fail)
