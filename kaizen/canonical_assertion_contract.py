"""
Canonical assertion layer: typed, trust-scored claims with explicit source refs.

Downstream strategy and collateral must consume assertions + research_decision_record,
not stitched freeform synthesis strings.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

CANONICAL_ASSERTION_CONTRACT_VERSION: Final[str] = "1.0"
RESEARCH_DECISION_RECORD_VERSION: Final[str] = "1.0"


class ClaimType(StrEnum):
    fact = "fact"
    inference = "inference"
    recommendation = "recommendation"
    risk = "risk"
    objection = "objection"
    persona_need = "persona_need"
    proof_requirement = "proof_requirement"


class ConfidenceLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class SourceTrust(StrEnum):
    strong = "strong"
    mixed = "mixed"
    weak = "weak"


class EvidenceStatus(StrEnum):
    validated = "validated"
    directional = "directional"
    caveated = "caveated"
    rejected = "rejected"


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(..., min_length=4, max_length=64)
    id: int = Field(..., ge=0)
    label: str = Field(default="", max_length=400)


class CanonicalAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., min_length=8, max_length=80)
    section: str = Field(..., min_length=4, max_length=64)
    claim: str = Field(..., min_length=12, max_length=2000)
    claim_type: ClaimType
    confidence: ConfidenceLevel
    source_refs: list[SourceRef] = Field(..., min_length=1)
    source_trust: SourceTrust
    evidence_status: EvidenceStatus
    eligible_for_downstream_messaging: bool
    rejection_reason: str | None = Field(default=None, max_length=800)
    notes_for_human_review: str | None = Field(default=None, max_length=1200)


class ApprovedCompetitiveContrast(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    named_alternative: str = Field(..., min_length=2, max_length=200)
    contrast_claim: str = Field(..., min_length=8, max_length=1200)
    approved: bool = True


class ResearchDecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=RESEARCH_DECISION_RECORD_VERSION, max_length=16)
    strategic_wedge: str = Field(..., min_length=4, max_length=1200)
    positioning_frame: str = Field(..., min_length=4, max_length=1200)
    icp_primary: str = Field(..., min_length=4, max_length=800)
    gtm_motion: str = Field(..., min_length=4, max_length=1200)
    proof_requirements: list[str] = Field(..., min_length=1)
    competitive_contrasts: list[ApprovedCompetitiveContrast] = Field(default_factory=list)
    positioning_conflict_detected: bool = False
    positioning_conflict_notes: str | None = Field(default=None, max_length=1200)

    @field_validator("proof_requirements", mode="before")
    @classmethod
    def _non_empty_strings(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_canonical_assertion_dict(data: dict[str, object]) -> CanonicalAssertion:
    return CanonicalAssertion.model_validate(data)


def validate_research_decision_record_dict(data: dict[str, object]) -> ResearchDecisionRecord:
    return ResearchDecisionRecord.model_validate(data)
