"""
Performance Review contract: interpretation layer after Performance Inputs Spec + operational metrics.

Consumes PerformanceInputsSpec structured payload, PerformanceInput aggregates, and upstream structured payloads.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

PERFORMANCE_REVIEW_CONTRACT_VERSION: Final[str] = "1.0"

PR_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Performance Review may: interpret observed signals against the Performance Inputs Spec and upstream "
    "execution artifacts; assess validation vs invalidation; recommend adjustments, hold-steady areas, and next "
    "instrumentation; and flag data gaps. It may not: become a raw metrics dashboard, casually rewrite strategy "
    "or invent a new wedge/ICP without framing as challenge or escalation, replace the Performance Inputs Spec "
    "as the measurement definition, or substitute raw corpus synthesis for upstream structured payloads."
)

PR_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


class PrObservedStatus(StrEnum):
    positive = "positive"
    mixed = "mixed"
    negative = "negative"
    insufficient_data = "insufficient_data"


class PrConfidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class PrActionRecommendation(StrEnum):
    hold = "hold"
    investigate = "investigate"
    adjust = "adjust"
    escalate = "escalate"


class ReviewAssessmentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    signal_name: str = Field(..., min_length=4, max_length=500)
    observed_status: PrObservedStatus
    interpretation: str = Field(..., min_length=8, max_length=1500)
    likely_implication: str = Field(..., min_length=8, max_length=1200)
    confidence: PrConfidence
    action_recommendation: PrActionRecommendation


class PrSupportingCollateralRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    collateral_type: str = Field(..., min_length=2)
    collateral_artifact_id: int | None = Field(default=None)
    reference_note: str = Field(default="", max_length=500)

    @field_validator("collateral_artifact_id")
    @classmethod
    def _id_positive_when_set(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("collateral_artifact_id must be >= 1 when set")
        return v


class PerformanceInputsSpecReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    performance_inputs_spec_id: int = Field(..., ge=1)
    performance_inputs_contract_version: str = Field(..., min_length=1, max_length=32)
    operational_input_row_count: int = Field(..., ge=0)
    measurement_goal_count: int = Field(..., ge=0)


class PerformanceReviewStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=PERFORMANCE_REVIEW_CONTRACT_VERSION)
    review_scope: str = Field(..., min_length=12, max_length=2500)
    signal_coverage: list[str] = Field(..., min_length=1)
    strategic_validation_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    message_resonance_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    asset_performance_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    sales_progression_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    channel_execution_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    digital_experience_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    risk_invalidation_assessment: list[ReviewAssessmentEntry] = Field(..., min_length=1)
    recommended_adjustments: list[str] = Field(..., min_length=1)
    hold_steady_areas: list[str] = Field(..., min_length=1)
    data_gaps: list[str] = Field(..., min_length=1)
    next_instrumentation_needs: list[str] = Field(..., min_length=1)
    supporting_collateral_refs: list[PrSupportingCollateralRef] = Field(default_factory=list)
    performance_inputs_reference: PerformanceInputsSpecReference
    message_spine_divergence_notes: str | None = None

    @field_validator(
        "signal_coverage",
        "recommended_adjustments",
        "hold_steady_areas",
        "data_gaps",
        "next_instrumentation_needs",
        "supporting_collateral_refs",
        mode="before",
    )
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_performance_review_payload_dict(data: dict[str, object]) -> PerformanceReviewStructuredPayload:
    return PerformanceReviewStructuredPayload.model_validate(data)


class PerformanceReviewFrameworkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
