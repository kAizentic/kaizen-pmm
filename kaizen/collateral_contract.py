"""
Typed collateral framework: shared contracts, transformation boundaries, and per-asset payloads.

Fully implemented: ``one_pager``, ``messaging_brief`` (structured peers). Additional ``CollateralArtifactTypeKey`` values are registry stubs
for future types (solution brief, landing page, etc.) without generators in this pass.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.artifact_quality_contract import OnePagerQualityReport
from kaizen.cross_artifact_consistency_contract import CrossArtifactConsistencyReport
from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

COLLATERAL_FRAMEWORK_VERSION: Final[str] = "1.0"
ONE_PAGER_CONTRACT_VERSION: Final[str] = "1.2"


class CollateralFrameworkError(Exception):
    """Typed collateral build failure (maps to HTTP in routers via CollateralError)."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


SHARED_COLLATERAL_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "Collateral execution may: compress upstream narrative into a channel-ready artifact, honor persona/stage/channel "
    "from the asset plan entry, prioritize a bounded set of proof points, and use reach-back only for proof/example/detail "
    "that does not re-decide strategy. It may not: reopen wedge, ICP, category frame, GTM motion, or strategic risk model; "
    "replace structured_decision_payload or structured_narrative_payload as sources of truth; emit generic undifferentiated "
    "copy; or substitute broad raw corpus synthesis for the committed pipeline layers."
)

COLLATERAL_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES

ONE_PAGER_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The One-Pager may: compress the message spine into a single-page GTM leave-behind, mirror the asset-plan one_pager "
    "objective and message_job, surface up to three proof highlights, and tune urgency tone to buying_stage. It may not: "
    "expand into whitepaper depth, invent new differentiation claims, add net-new strategic options, or omit a clear CTA."
)

ONE_PAGER_PROOF_RULES: Final[str] = (
    "Proof highlights must come from message spine proof_points and/or strategy proof_requirements ordering; at most three "
    "bullets; no fabricated metrics; if a slot is thin, reference the proof_required field from the asset plan entry in "
    "plain language without inventing data."
)


class CollateralArtifactTypeKey(StrEnum):
    """Registry of collateral asset_type string keys (existing API values + planned stubs)."""

    executive_brief = "executive_brief"
    one_pager = "one_pager"
    messaging_brief = "messaging_brief"
    sales_deck = "sales_deck"
    whitepaper = "whitepaper"
    proof_template = "proof_template"
    social = "social"
    website_copy = "website_copy"
    # --- Planned (no generator in this pass) ---
    solution_brief = "solution_brief"
    landing_page_copy = "landing_page_copy"
    benchmark_summary = "benchmark_summary"
    executive_memo = "executive_memo"
    webinar_brief = "webinar_brief"
    case_study_shell = "case_study_shell"


TYPED_COLLATERAL_IMPLEMENTED: Final[frozenset[str]] = frozenset(
    {CollateralArtifactTypeKey.one_pager, CollateralArtifactTypeKey.messaging_brief},
)


class OnePagerHumanSection(StrEnum):
    headline_category = "headline_category"
    problem_statement = "problem_statement"
    why_now = "why_now"
    product_definition = "product_definition"
    differentiators = "differentiators"
    proof_highlights = "proof_highlights"
    who_its_for = "who_its_for"
    why_buyers_move = "why_buyers_move"
    cta = "cta"


ONE_PAGER_HUMAN_SECTION_ORDER: Final[tuple[OnePagerHumanSection, ...]] = (
    OnePagerHumanSection.headline_category,
    OnePagerHumanSection.problem_statement,
    OnePagerHumanSection.why_now,
    OnePagerHumanSection.product_definition,
    OnePagerHumanSection.differentiators,
    OnePagerHumanSection.proof_highlights,
    OnePagerHumanSection.who_its_for,
    OnePagerHumanSection.why_buyers_move,
    OnePagerHumanSection.cta,
)


class AssetPlanReferenceBlock(BaseModel):
    """Links this collateral row to the planning entry that authorized it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_plan_id: int = Field(..., ge=1)
    priority_rank: int = Field(..., ge=1, le=99)
    planning_objective: str = Field(..., min_length=4)
    message_job: str = Field(..., min_length=4)
    proof_required_from_plan: str = Field(..., min_length=2)
    dependency_assets: list[str] = Field(default_factory=list)

    @field_validator("dependency_assets", mode="before")
    @classmethod
    def _deps(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


class OnePagerStructuredPayload(BaseModel):
    """Strict machine-readable one-pager for downstream packagers and QA."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=ONE_PAGER_CONTRACT_VERSION)
    collateral_type: str = Field(default="one_pager", min_length=6)
    target_persona: str = Field(..., min_length=2)
    buying_stage: str = Field(..., min_length=3)
    channel: str = Field(..., min_length=2)
    headline: str = Field(..., min_length=8)
    category_line: str = Field(..., min_length=6)
    problem_statement: str = Field(..., min_length=12)
    urgency_statement: str = Field(..., min_length=12)
    product_definition: str = Field(..., min_length=12)
    differentiators: list[str] = Field(..., min_length=1, max_length=5)
    proof_highlights: list[str] = Field(..., min_length=1, max_length=3)
    target_buyer_summary: str = Field(..., min_length=8)
    buying_trigger: str = Field(..., min_length=8)
    cta: str = Field(..., min_length=12)
    subhead: str = Field(default="", max_length=400)
    fallback_used: bool = Field(default=False)
    fallback_reason: str | None = Field(default=None, max_length=500)
    supporting_asset_dependencies: list[str] = Field(default_factory=list)
    asset_plan_reference: AssetPlanReferenceBlock
    message_spine_divergence_notes: str | None = None
    quality_report: OnePagerQualityReport | None = Field(
        default=None,
        description="Artifact-level QA scores and pass status.",
    )
    rewrite_applied: bool = Field(default=False)
    rewrite_reason: str | None = Field(default=None, max_length=800)
    cross_artifact_consistency_report: CrossArtifactConsistencyReport | None = Field(
        default=None,
        description="Cross-artifact narrative consistency vs sibling shapes / PMM.",
    )
    cross_artifact_normalization_applied: bool = Field(default=False)
    cross_artifact_normalization_reason: str | None = Field(default=None, max_length=1600)

    @field_validator("differentiators", "proof_highlights", "supporting_asset_dependencies", mode="before")
    @classmethod
    def _str_lists(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


def validate_one_pager_payload_dict(data: dict[str, object]) -> OnePagerStructuredPayload:
    return OnePagerStructuredPayload.model_validate(data)
