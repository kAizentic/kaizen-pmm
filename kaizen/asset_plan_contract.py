"""
Asset Plan artifact contract (v1): production-planning layer after the Message Spine.

Maps committed strategy and narrative into prioritized assets, dependencies, and reuse logic.
Generation consumes ``MessageSpine.structured_narrative_payload`` first and
``StrategyBrief.structured_decision_payload`` as strategic control input.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

ASSET_PLAN_CONTRACT_VERSION: Final[str] = "1.0"

TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Asset Plan may: prioritize and sequence assets, map them to personas, buying stages, and channels, "
    "name proof and production dependencies, and define reuse across deliverables. It may not: re-open wedge, "
    "ICP, category frame, GTM motion, strategic risks, or rewrite the message spine; substitute broad raw corpus "
    "intelligence for planning; or become a generic content wishlist. Bounded reach-back is for proof/example "
    "detail only (see reachback_policy)."
)


class AssetPlanHumanSection(StrEnum):
    planning_assumptions = "planning_assumptions"
    priority_asset_sequence = "priority_asset_sequence"
    asset_matrix = "asset_matrix"
    proof_dependencies = "proof_dependencies"
    production_dependencies = "production_dependencies"
    reuse_modularity = "reuse_modularity"
    near_term_recommendations = "near_term_recommendations"
    deferred_assets = "deferred_assets"


ASSET_PLAN_HUMAN_SECTION_ORDER: Final[tuple[AssetPlanHumanSection, ...]] = (
    AssetPlanHumanSection.planning_assumptions,
    AssetPlanHumanSection.priority_asset_sequence,
    AssetPlanHumanSection.asset_matrix,
    AssetPlanHumanSection.proof_dependencies,
    AssetPlanHumanSection.production_dependencies,
    AssetPlanHumanSection.reuse_modularity,
    AssetPlanHumanSection.near_term_recommendations,
    AssetPlanHumanSection.deferred_assets,
)

# Maps contract concepts to existing asset_plans table columns (human markdown).
LEGACY_ASSET_PLAN_COLUMN_BY_CONCEPT: Final[dict[str, str]] = {
    "planning_assumptions": "executive_brief_plan",
    "priority_asset_sequence": "one_pager_plan",
    "asset_matrix": "sales_deck_plan",
    "proof_dependencies": "whitepaper_plan",
    "production_dependencies": "proof_template_plan",
    "reuse_modularity": "social_campaign_plan",
    "near_term_recommendations": "website_copy_plan",
    "deferred_assets": "rationale",
}


class PrioritizedAssetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_type: str = Field(
        ...,
        min_length=3,
        description="Collateral / plan type key (e.g. executive_brief, proof_template).",
    )
    target_persona: str = Field(..., min_length=2)
    buying_stage: str = Field(
        ...,
        min_length=3,
        description="e.g. awareness, consideration, validation, expansion",
    )
    channel: str = Field(..., min_length=2)
    objective: str = Field(..., min_length=8)
    message_job: str = Field(..., min_length=8)
    proof_required: str = Field(..., min_length=4)
    production_effort: str = Field(
        ...,
        min_length=3,
        description="low | medium | high",
    )
    dependency_assets: list[str] = Field(default_factory=list)
    priority_rank: int = Field(..., ge=1, le=99)

    @field_validator("dependency_assets", mode="before")
    @classmethod
    def _coerce_deps(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


class AssetPlanStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=ASSET_PLAN_CONTRACT_VERSION)

    planning_assumptions: list[str] = Field(..., min_length=1)
    prioritized_assets: list[PrioritizedAssetEntry] = Field(..., min_length=1)
    asset_matrix: list[str] = Field(
        ...,
        min_length=1,
        description="Rows: persona | stage | channel | asset focus | message role",
    )
    proof_dependencies: list[str] = Field(..., min_length=1)
    production_dependencies: list[str] = Field(..., min_length=1)
    reuse_modules: list[str] = Field(default_factory=list)
    near_term_recommendations: list[str] = Field(..., min_length=1)
    deferred_assets: list[str] = Field(default_factory=list)
    downstream_channel_implications: list[str] = Field(..., min_length=2)
    message_spine_divergence_notes: str | None = Field(
        default=None,
        description="Echo message-spine / strategy divergence; asset plan does not resolve.",
    )

    @field_validator(
        "planning_assumptions",
        "asset_matrix",
        "proof_dependencies",
        "production_dependencies",
        "reuse_modules",
        "near_term_recommendations",
        "deferred_assets",
        "downstream_channel_implications",
        mode="before",
    )
    @classmethod
    def _coerce_str_lists(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v

    @field_validator("prioritized_assets", mode="before")
    @classmethod
    def _coerce_assets(cls, v: object) -> object:
        if v is None:
            return []
        return v


MESSAGE_SPINE_PAYLOAD_FIELD_FEEDS: Final[dict[str, tuple[str, ...]]] = {
    "planning_assumptions": ("master_narrative", "messaging_guardrails", "downstream_asset_implications"),
    "prioritized_assets": ("persona_message_hierarchy", "proof_points", "cta_logic", "value_pillars"),
    "asset_matrix": ("persona_message_hierarchy", "content_angle_seeds"),
    "proof_dependencies": ("proof_points", "objection_map"),
    "production_dependencies": ("downstream_asset_implications", "cta_logic"),
    "reuse_modules": ("value_pillars", "master_narrative"),
    "near_term_recommendations": ("cta_logic", "content_angle_seeds"),
    "deferred_assets": ("forbidden_language", "messaging_guardrails"),
    "downstream_channel_implications": ("downstream_asset_implications",),
    "message_spine_divergence_notes": ("strategy_brief_divergence_notes",),
}

STRATEGY_PAYLOAD_CONTROL_FEEDS: Final[dict[str, tuple[str, ...]]] = {
    "prioritized_assets": ("proof_requirements", "preferred_gtm_motion", "rejected_gtm_motions", "recommended_icp"),
    "proof_dependencies": ("proof_requirements", "key_adoption_blockers"),
    "planning_assumptions": ("decision_rationale", "strategic_risks"),
    "deferred_assets": ("rejected_gtm_motions", "excluded_icps"),
}

ASSET_PLAN_CORPUS_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES

DOWNSTREAM_CONSUMED_ASSET_PLAN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "planning_assumptions",
        "prioritized_assets",
        "asset_matrix",
        "proof_dependencies",
        "production_dependencies",
        "reuse_modules",
        "near_term_recommendations",
        "deferred_assets",
        "downstream_channel_implications",
        "message_spine_divergence_notes",
    },
)


def validate_asset_plan_payload_dict(data: dict[str, object]) -> AssetPlanStructuredPayload:
    return AssetPlanStructuredPayload.model_validate(data)
