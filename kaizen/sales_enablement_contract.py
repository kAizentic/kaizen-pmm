"""
Sales Enablement Brief contract: deal-execution layer after Strategy, Message Spine, and Asset Plan.

Consumes structured payloads from those artifacts; optional typed One-Pager as supporting reference only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

SALES_ENABLEMENT_CONTRACT_VERSION: Final[str] = "1.0"

SEB_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Sales Enablement Brief may: operationalize the message spine for live selling, prioritize discovery "
    "and proof sequences, map objections to proof artifacts and planned collateral, name competitive traps "
    "and qualification logic, and tie next steps to the asset plan. It may not: rewrite strategy, invent a "
    "new wedge or ICP, replace upstream structured payloads as truth, become a generic call script, or "
    "substitute raw corpus synthesis for committed pipeline layers."
)

SEB_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


class SebHumanSection(StrEnum):
    deal_narrative = "deal_narrative"
    buyer_coalition = "buyer_coalition"
    lead_vs_win_over = "lead_vs_win_over"
    discovery_priorities = "discovery_priorities"
    proof_requirements = "proof_requirements"
    objections_skepticism = "objections_skepticism"
    competitive_traps = "competitive_traps"
    qualification_signals = "qualification_signals"
    disqualification_signals = "disqualification_signals"
    next_step_assets = "next_step_assets"
    deal_progression = "deal_progression"


SEB_HUMAN_SECTION_ORDER: Final[tuple[SebHumanSection, ...]] = (
    SebHumanSection.deal_narrative,
    SebHumanSection.buyer_coalition,
    SebHumanSection.lead_vs_win_over,
    SebHumanSection.discovery_priorities,
    SebHumanSection.proof_requirements,
    SebHumanSection.objections_skepticism,
    SebHumanSection.competitive_traps,
    SebHumanSection.qualification_signals,
    SebHumanSection.disqualification_signals,
    SebHumanSection.next_step_assets,
    SebHumanSection.deal_progression,
)


class CoalitionBuyerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: str = Field(..., min_length=2)
    priority: str = Field(
        ...,
        min_length=3,
        description="lead | win_over | supporting",
    )
    cares_about: str = Field(..., min_length=4)
    fears: str = Field(default="", max_length=2000)
    proof_they_need: str = Field(default="", max_length=2000)


class SupportingCollateralRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    collateral_type: str = Field(..., min_length=3)
    collateral_artifact_id: int | None = Field(default=None, ge=1)
    reference_note: str = Field(
        default="",
        description="Supporting reference only; spine and strategy payloads remain canonical.",
    )


class SebAssetPlanReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_plan_id: int = Field(..., ge=1)
    prioritized_asset_sequence: list[str] = Field(
        ...,
        min_length=1,
        description="Ordered asset_type keys from the plan (machine sequence).",
    )
    proof_dependency_echo: list[str] = Field(default_factory=list)


class SalesEnablementStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SALES_ENABLEMENT_CONTRACT_VERSION)
    deal_narrative: str = Field(..., min_length=24)
    buyer_coalition: list[CoalitionBuyerEntry] = Field(..., min_length=1)
    lead_buyer: str = Field(..., min_length=2)
    win_over_buyers: list[str] = Field(default_factory=list)
    discovery_questions: list[str] = Field(..., min_length=3)
    proof_requirements: list[str] = Field(..., min_length=1)
    objection_map: list[str] = Field(..., min_length=1)
    competitive_traps: list[str] = Field(..., min_length=1)
    qualification_signals: list[str] = Field(..., min_length=1)
    disqualification_signals: list[str] = Field(..., min_length=1)
    next_step_assets: list[str] = Field(..., min_length=1)
    deal_progression_guidance: str = Field(..., min_length=12)
    supporting_collateral_refs: list[SupportingCollateralRef] = Field(default_factory=list)
    asset_plan_reference: SebAssetPlanReference
    message_spine_divergence_notes: str | None = None

    @field_validator(
        "win_over_buyers",
        "discovery_questions",
        "proof_requirements",
        "objection_map",
        "competitive_traps",
        "qualification_signals",
        "disqualification_signals",
        "next_step_assets",
        "supporting_collateral_refs",
        mode="before",
    )
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_sales_enablement_payload_dict(data: dict[str, object]) -> SalesEnablementStructuredPayload:
    return SalesEnablementStructuredPayload.model_validate(data)


class SalesEnablementFrameworkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
