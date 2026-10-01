"""
Performance Inputs spec contract: measurement-definition layer after Strategy, Spine, AP, SEB, CEP, and DX.

Consumes structured payloads from those artifacts; typed collateral rows are supporting references only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

PERFORMANCE_INPUTS_CONTRACT_VERSION: Final[str] = "1.0"

PI_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "Performance Inputs may: define what should be measured, map signals to upstream artifact layers, distinguish "
    "success from invalidation signals, prioritize instrumentation work, and assign provisional owners and cadence. "
    "They may not: become a dashboard or analysis report, rewrite strategy, invent a wedge or ICP, replace channel "
    "or asset plans as truth, or substitute raw corpus synthesis for upstream structured payloads."
)

PI_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


class PiSignalLevel(StrEnum):
    strategy = "strategy"
    message = "message"
    asset = "asset"
    sales = "sales"
    channel = "channel"
    digital_experience = "digital_experience"
    risk = "risk"


class PiSignalType(StrEnum):
    quantitative = "quantitative"
    qualitative = "qualitative"
    hybrid = "hybrid"


class PiLeadingLagging(StrEnum):
    leading = "leading"
    lagging = "lagging"
    mixed = "mixed"


class PiHumanSection(StrEnum):
    measurement_goals = "measurement_goals"
    strategic_success = "strategic_success"
    message_resonance = "message_resonance"
    asset_performance = "asset_performance"
    sales_progression = "sales_progression"
    channel_performance = "channel_performance"
    digital_experience = "digital_experience"
    risk_invalidation = "risk_invalidation"
    signal_owners = "signal_owners"
    instrumentation_priorities = "instrumentation_priorities"
    deferred_instrumentation = "deferred_instrumentation"


PI_HUMAN_SECTION_ORDER: Final[tuple[PiHumanSection, ...]] = (
    PiHumanSection.measurement_goals,
    PiHumanSection.strategic_success,
    PiHumanSection.message_resonance,
    PiHumanSection.asset_performance,
    PiHumanSection.sales_progression,
    PiHumanSection.channel_performance,
    PiHumanSection.digital_experience,
    PiHumanSection.risk_invalidation,
    PiHumanSection.signal_owners,
    PiHumanSection.instrumentation_priorities,
    PiHumanSection.deferred_instrumentation,
)


class PerformanceSignalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    signal_name: str = Field(..., min_length=4, max_length=400)
    signal_level: PiSignalLevel
    signal_type: PiSignalType
    why_it_matters: str = Field(..., min_length=8, max_length=1200)
    source_layer: str = Field(
        ...,
        min_length=4,
        max_length=120,
        description="Upstream artifact or field group (e.g. strategy_brief.structured_decision_payload).",
    )
    collection_method: str = Field(..., min_length=4, max_length=500)
    owner: str = Field(..., min_length=2, max_length=200)
    cadence: str = Field(..., min_length=2, max_length=120)
    leading_or_lagging: PiLeadingLagging
    success_condition: str = Field(..., min_length=4, max_length=800)
    risk_condition: str = Field(default="", max_length=800)


class PiSupportingCollateralRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    collateral_type: str = Field(..., min_length=2)
    collateral_artifact_id: int | None = Field(default=None, ge=1)
    reference_note: str = Field(default="", max_length=500)


class PiAssetPlanReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_plan_id: int = Field(..., ge=1)
    prioritized_asset_sequence: list[str] = Field(..., min_length=1)
    proof_dependency_echo: list[str] = Field(default_factory=list)


class PerformanceInputsStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=PERFORMANCE_INPUTS_CONTRACT_VERSION)
    measurement_goals: list[str] = Field(..., min_length=1)
    strategic_success_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    message_resonance_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    asset_performance_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    sales_progression_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    channel_performance_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    digital_experience_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    risk_invalidation_signals: list[PerformanceSignalEntry] = Field(..., min_length=1)
    signal_owners: list[str] = Field(..., min_length=1)
    instrumentation_priorities: list[str] = Field(..., min_length=1)
    deferred_instrumentation: list[str] = Field(default_factory=list)
    supporting_collateral_refs: list[PiSupportingCollateralRef] = Field(default_factory=list)
    asset_plan_reference: PiAssetPlanReference
    message_spine_divergence_notes: str | None = None

    @field_validator(
        "measurement_goals",
        "signal_owners",
        "instrumentation_priorities",
        "deferred_instrumentation",
        "supporting_collateral_refs",
        mode="before",
    )
    @classmethod
    def _str_lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_performance_inputs_payload_dict(data: dict[str, object]) -> PerformanceInputsStructuredPayload:
    return PerformanceInputsStructuredPayload.model_validate(data)


class PerformanceInputsFrameworkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
