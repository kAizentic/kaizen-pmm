"""
Cross-artifact consistency: unified narrative checks across one-pager, channel plan, messaging brief.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

CROSS_ARTIFACT_CONSISTENCY_CONTRACT_VERSION: Final[str] = "1.0"


class AlignmentSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class ArtifactAlignmentNote(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_a: str = Field(..., min_length=2, max_length=64)
    artifact_b: str = Field(..., min_length=2, max_length=64)
    dimension: str = Field(..., min_length=2, max_length=80)
    issue: str = Field(..., min_length=4, max_length=1200)
    severity: AlignmentSeverity = Field(default=AlignmentSeverity.medium)
    suggested_fix: str = Field(default="", max_length=1200)


class CrossArtifactConsistencyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=CROSS_ARTIFACT_CONSISTENCY_CONTRACT_VERSION, max_length=16)
    overall_consistency_score: float = Field(..., ge=0.0, le=1.0)
    wedge_alignment_score: float = Field(..., ge=0.0, le=1.0)
    positioning_alignment_score: float = Field(..., ge=0.0, le=1.0)
    icp_alignment_score: float = Field(..., ge=0.0, le=1.0)
    pain_alignment_score: float = Field(..., ge=0.0, le=1.0)
    proof_alignment_score: float = Field(..., ge=0.0, le=1.0)
    contrast_alignment_score: float = Field(..., ge=0.0, le=1.0)
    gtm_alignment_score: float = Field(..., ge=0.0, le=1.0)
    metric_alignment_score: float = Field(..., ge=0.0, le=1.0)
    buyer_language_alignment_score: float = Field(..., ge=0.0, le=1.0)
    contradiction_flags: list[str] = Field(default_factory=list)
    drift_flags: list[str] = Field(default_factory=list)
    omission_flags: list[str] = Field(default_factory=list)
    normalization_suggestions: list[str] = Field(default_factory=list)
    artifact_pair_notes: dict[str, str] = Field(default_factory=dict)
    alignment_notes: list[ArtifactAlignmentNote] = Field(default_factory=list)
    normalization_applied: bool = Field(default=False)
    normalization_reason: str | None = Field(default=None, max_length=1600)
