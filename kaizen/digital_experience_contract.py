"""
Digital Experience Spec contract: digital-surface execution layer after Strategy, Spine, AP, SEB, and CEP.

Consumes structured payloads from those artifacts; typed collateral rows are supporting references only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

DIGITAL_EXPERIENCE_CONTRACT_VERSION: Final[str] = "1.0"

DX_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Digital Experience Spec may: prioritize pages and modules, define narrative and CTA hierarchy per surface, "
    "assign proof and trust modules, describe persona routing, map planned assets to surfaces, name reusable section "
    "systems, and encode friction reduction logic for digital buyers. It may not: rewrite strategy, invent a "
    "wedge or ICP, output final marketing copy or visual design, replace the asset plan or channel plan as truth, "
    "or substitute raw corpus synthesis for upstream structured payloads."
)

DX_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


class DxHumanSection(StrEnum):
    experience_goals = "experience_goals"
    priority_surfaces = "priority_surfaces"
    narrative_hierarchy = "narrative_hierarchy"
    cta_hierarchy = "cta_hierarchy"
    proof_trust_modules = "proof_trust_modules"
    persona_routing = "persona_routing"
    asset_embedding = "asset_embedding"
    reusable_modules = "reusable_modules"
    friction_reduction = "friction_reduction"
    early_implementation = "early_implementation"
    deferred_surfaces = "deferred_surfaces"


DX_HUMAN_SECTION_ORDER: Final[tuple[DxHumanSection, ...]] = (
    DxHumanSection.experience_goals,
    DxHumanSection.priority_surfaces,
    DxHumanSection.narrative_hierarchy,
    DxHumanSection.cta_hierarchy,
    DxHumanSection.proof_trust_modules,
    DxHumanSection.persona_routing,
    DxHumanSection.asset_embedding,
    DxHumanSection.reusable_modules,
    DxHumanSection.friction_reduction,
    DxHumanSection.early_implementation,
    DxHumanSection.deferred_surfaces,
)


class PrioritizedSurfaceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    surface_name: str = Field(..., min_length=4)
    priority_rank: int = Field(..., ge=1, le=99)
    objective: str = Field(..., min_length=8)
    target_persona: str = Field(..., min_length=2)
    buying_stage: str = Field(..., min_length=3)
    primary_message: str = Field(..., min_length=8)
    supporting_proof: str = Field(..., min_length=4)
    primary_cta: str = Field(..., min_length=4)
    secondary_cta: str = Field(default="", max_length=600)
    linked_assets: list[str] = Field(..., min_length=1)
    dependency_surfaces: list[str] = Field(default_factory=list)

    @field_validator("linked_assets", "dependency_surfaces", mode="before")
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


class DxSupportingCollateralRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    collateral_type: str = Field(..., min_length=2)
    collateral_artifact_id: int | None = Field(default=None, ge=1)
    reference_note: str = Field(default="", description="Which surfaces benefit; supporting reference only.")


class DxAssetPlanReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_plan_id: int = Field(..., ge=1)
    prioritized_asset_sequence: list[str] = Field(..., min_length=1)
    proof_dependency_echo: list[str] = Field(default_factory=list)


class DigitalExperienceStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=DIGITAL_EXPERIENCE_CONTRACT_VERSION)
    experience_goals: list[str] = Field(..., min_length=1)
    prioritized_surfaces: list[PrioritizedSurfaceEntry] = Field(..., min_length=1)
    page_role_map: list[str] = Field(..., min_length=1)
    page_narrative_map: list[str] = Field(..., min_length=1)
    cta_hierarchy: list[str] = Field(..., min_length=1)
    proof_module_map: list[str] = Field(..., min_length=1)
    trust_module_map: list[str] = Field(..., min_length=1)
    persona_routing_logic: list[str] = Field(..., min_length=1)
    asset_embedding_map: list[str] = Field(..., min_length=1)
    reusable_modules: list[str] = Field(..., min_length=1)
    friction_reduction_rules: list[str] = Field(..., min_length=1)
    early_implementation_recommendations: list[str] = Field(..., min_length=1)
    deferred_surfaces: list[str] = Field(default_factory=list)
    supporting_collateral_refs: list[DxSupportingCollateralRef] = Field(default_factory=list)
    asset_plan_reference: DxAssetPlanReference
    message_spine_divergence_notes: str | None = None

    @field_validator(
        "experience_goals",
        "page_role_map",
        "page_narrative_map",
        "cta_hierarchy",
        "proof_module_map",
        "trust_module_map",
        "persona_routing_logic",
        "asset_embedding_map",
        "reusable_modules",
        "friction_reduction_rules",
        "early_implementation_recommendations",
        "deferred_surfaces",
        "supporting_collateral_refs",
        mode="before",
    )
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_digital_experience_payload_dict(data: dict[str, object]) -> DigitalExperienceStructuredPayload:
    return DigitalExperienceStructuredPayload.model_validate(data)


class DigitalExperienceFrameworkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
