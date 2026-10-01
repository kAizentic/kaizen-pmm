"""
Strategy Brief artifact contract (v1): decision layer after the Research Brief.

This module defines the human-readable section intent, the machine-readable structured payload
shape, primary inputs (research brief signal classes), and transformation boundaries.

Payload construction for persistence lives in the strategy-brief stage skill; this module holds
the contract, validation helpers, and maps that downstream artifacts (message spine consumes ``structured_decision_payload`` first; asset plan,
enablement, channel, collateral) will consume.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

STRATEGY_BRIEF_CONTRACT_VERSION: Final[str] = "2.0"

# Transformation boundaries (normative for generators).
TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Strategy Brief may: interpret research signals, prioritize options, commit to choices, and name "
    "explicit non-choices. It may not: act as a generic recap of the research brief, re-ingest the full "
    "raw scenario corpus for core wedge/ICP/category/GTM decisions, or contradict the research brief without "
    "documenting rationale in research_brief_divergence_notes. Bounded corpus reach-back is permitted only "
    "for proof, examples, competitor detail, evidence recovery, or appendix support (see reachback_policy)."
)


class StrategyBriefHumanSection(StrEnum):
    """Stable IDs for operator-facing markdown sections (decision-layer intent, not research recap)."""

    strategic_recommendation = "strategic_recommendation"
    priority_icp = "priority_icp"
    problem_framing = "problem_framing"
    strategic_wedge = "strategic_wedge"
    category_positioning_decision = "category_positioning_decision"
    differentiation_logic = "differentiation_logic"
    mandatory_proof_model = "mandatory_proof_model"
    recommended_gtm_motion = "recommended_gtm_motion"
    adoption_blockers = "adoption_blockers"
    strategic_risks = "strategic_risks"
    immediate_next_strategic_moves = "immediate_next_strategic_moves"


# Ordered presentation for UIs / templates (11 sections).
STRATEGY_BRIEF_HUMAN_SECTION_ORDER: Final[tuple[StrategyBriefHumanSection, ...]] = (
    StrategyBriefHumanSection.strategic_recommendation,
    StrategyBriefHumanSection.priority_icp,
    StrategyBriefHumanSection.problem_framing,
    StrategyBriefHumanSection.strategic_wedge,
    StrategyBriefHumanSection.category_positioning_decision,
    StrategyBriefHumanSection.differentiation_logic,
    StrategyBriefHumanSection.mandatory_proof_model,
    StrategyBriefHumanSection.recommended_gtm_motion,
    StrategyBriefHumanSection.adoption_blockers,
    StrategyBriefHumanSection.strategic_risks,
    StrategyBriefHumanSection.immediate_next_strategic_moves,
)

SECTION_INTENT: Final[dict[StrategyBriefHumanSection, str]] = {
    StrategyBriefHumanSection.strategic_recommendation: (
        "Single committed recommendation: what we choose to do and optimize for next."
    ),
    StrategyBriefHumanSection.priority_icp: "Who we prioritize and who is explicitly deprioritized.",
    StrategyBriefHumanSection.problem_framing: "Primary problem frame the strategy bets on (not a pain list dump).",
    StrategyBriefHumanSection.strategic_wedge: "The wedge we commit to versus alternatives named in research.",
    StrategyBriefHumanSection.category_positioning_decision: "Category / positioning choice we are buying, not exploring.",
    StrategyBriefHumanSection.differentiation_logic: "Why buyers should believe we win vs named failure modes.",
    StrategyBriefHumanSection.mandatory_proof_model: "Non-negotiable proof artifacts and gates before scale.",
    StrategyBriefHumanSection.recommended_gtm_motion: "Winning GTM motion first; others sequenced or rejected.",
    StrategyBriefHumanSection.adoption_blockers: "Structural blockers to plan around, not generic objections.",
    StrategyBriefHumanSection.strategic_risks: "Risks that can invalidate the strategy if wrong.",
    StrategyBriefHumanSection.immediate_next_strategic_moves: "Next strategic actions (not a task backlog).",
}


class CategoryStyle(StrEnum):
    """Dunford's four framing styles; ``new`` (category creation) is the hardest to execute."""

    existing = "existing"
    subsegment = "subsegment"
    reframe = "reframe"
    new = "new"


class Exclusion(BaseModel):
    """A deliberate non-choice: what we are not doing, why, and the evidence that it was a real option."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item: str = Field(..., min_length=4)
    reason: str = Field(..., min_length=12, description="Why this option is rejected now.")
    evidence: list[str] = Field(..., min_length=1, description="Evidence ids showing this was a real option.")


class Assumption(BaseModel):
    """Something that must be true for the strategy to work, with the observation that would disprove it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    assumption: str = Field(..., min_length=12)
    what_would_falsify: str = Field(..., min_length=12)


class StrategyBriefStructuredPayload(BaseModel):
    """
    Machine-readable decision payload for downstream generators.

    Must be derivable primarily from the approved research brief narrative + evidence_table;
    scenario corpus reach-back is allowed only for bounded proof/detail enrichment (see contract docs).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=STRATEGY_BRIEF_CONTRACT_VERSION)

    strategic_recommendation: str = Field(
        ...,
        min_length=12,
        description="Committed choice: what we are doing; must not read as a research summary.",
    )
    recommended_icp: str = Field(..., min_length=8, description="Primary ICP we will win first.")
    excluded_icps: list[Exclusion] = Field(
        ...,
        min_length=1,
        description="Explicit non-choices or deprioritized segments, each with a reason and evidence.",
    )
    problem_frame: str = Field(
        ...,
        min_length=12,
        description="Single dominant problem frame the strategy assumes (prioritized vs research).",
    )
    wedge: str = Field(..., min_length=8, description="Strategic wedge commitment aligned to research brief.")
    category_frame: str = Field(
        ...,
        min_length=8,
        description="Category / positioning frame we commit to (not exploratory options).",
    )
    category_style: CategoryStyle = Field(
        ...,
        description="existing | subsegment | reframe | new (new = category creation, highest proof burden).",
    )
    differentiation_claim: str = Field(
        ...,
        min_length=12,
        description="Core differentiation logic buyers must believe for the strategy to work.",
    )
    proof_requirements: list[str] = Field(
        default_factory=list,
        description="Mandatory proof artifacts, benchmarks, or procurement gates.",
    )
    preferred_gtm_motion: str = Field(..., min_length=6, description="GTM motion we lead with.")
    rejected_gtm_motions: list[Exclusion] = Field(
        ...,
        min_length=1,
        description="GTM paths explicitly not chosen now, each with a reason and evidence.",
    )
    key_adoption_blockers: list[str] = Field(
        default_factory=list,
        description="Adoption / process blockers the plan must neutralize.",
    )
    strategic_risks: list[str] = Field(
        default_factory=list,
        description="Strategy-invalidating risks (not a generic risk laundry list).",
    )
    assumptions: list[Assumption] = Field(
        ...,
        min_length=1,
        description="What must be true for this strategy to work, each with what would falsify it.",
    )
    decision_rationale: str = Field(
        ...,
        min_length=24,
        description="Why these choices follow from research; required when constraining ambiguity.",
    )
    dependent_message_requirements: list[str] = Field(
        default_factory=list,
        description="What messaging / narrative spine must carry for this strategy to land.",
    )
    immediate_next_strategic_moves: list[str] = Field(
        default_factory=list,
        description="Immediate strategic moves (3–7 bullets typical).",
    )
    research_brief_divergence_notes: str | None = Field(
        default=None,
        description="If any choice diverges from the research brief, explicit rationale must appear here.",
    )

    @field_validator(
        "proof_requirements",
        "key_adoption_blockers",
        "strategic_risks",
        "dependent_message_requirements",
        "immediate_next_strategic_moves",
        mode="before",
    )
    @classmethod
    def _coerce_list_items(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


# --- Research Brief dependencies (primary input path) ---

# Signal class → research brief fields / blocks that should inform strategy decisions.
class ResearchBriefSignalClass(StrEnum):
    market_structure_sam = "market_structure_sam"
    strategic_wedge_candidates = "strategic_wedge_candidates"
    embedded_threats = "embedded_threats"
    buyer_process_friction = "buyer_process_friction"
    gtm_motion_tradeoffs = "gtm_motion_tradeoffs"
    proof_burden = "proof_burden"
    risk_classes = "risk_classes"
    adoption_horizon = "adoption_horizon"
    competitive_landscape = "competitive_landscape"
    emerging_signals = "emerging_signals"
    key_problems = "key_problems"


# Maps structured payload fields to the research-brief signal classes that primarily feed them.
# Corpus reach-back must not substitute for these when the research brief already contains them.
RESEARCH_BRIEF_FIELD_SIGNAL_FEEDS: Final[dict[str, tuple[ResearchBriefSignalClass, ...]]] = {
    "strategic_recommendation": (
        ResearchBriefSignalClass.key_problems,
        ResearchBriefSignalClass.strategic_wedge_candidates,
        ResearchBriefSignalClass.market_structure_sam,
    ),
    "recommended_icp": (ResearchBriefSignalClass.buyer_process_friction,),
    "excluded_icps": (ResearchBriefSignalClass.buyer_process_friction,),
    "problem_frame": (
        ResearchBriefSignalClass.key_problems,
        ResearchBriefSignalClass.buyer_process_friction,
    ),
    "wedge": (ResearchBriefSignalClass.strategic_wedge_candidates,),
    "category_frame": (
        ResearchBriefSignalClass.competitive_landscape,
        ResearchBriefSignalClass.market_structure_sam,
    ),
    "differentiation_claim": (
        ResearchBriefSignalClass.embedded_threats,
        ResearchBriefSignalClass.competitive_landscape,
    ),
    "proof_requirements": (ResearchBriefSignalClass.proof_burden,),
    "preferred_gtm_motion": (ResearchBriefSignalClass.gtm_motion_tradeoffs,),
    "rejected_gtm_motions": (ResearchBriefSignalClass.gtm_motion_tradeoffs,),
    "key_adoption_blockers": (
        ResearchBriefSignalClass.buyer_process_friction,
        ResearchBriefSignalClass.proof_burden,
    ),
    "strategic_risks": (
        ResearchBriefSignalClass.risk_classes,
        ResearchBriefSignalClass.embedded_threats,
    ),
    "decision_rationale": tuple(ResearchBriefSignalClass),
    "dependent_message_requirements": (
        ResearchBriefSignalClass.strategic_wedge_candidates,
        ResearchBriefSignalClass.competitive_landscape,
        ResearchBriefSignalClass.market_structure_sam,
    ),
    "immediate_next_strategic_moves": (
        ResearchBriefSignalClass.key_problems,
        ResearchBriefSignalClass.gtm_motion_tradeoffs,
    ),
}


# Where each signal class is expected to appear on the ResearchBrief row (primary generator input).
RESEARCH_BRIEF_SIGNAL_SOURCE_FIELDS: Final[dict[ResearchBriefSignalClass, tuple[str, ...]]] = {
    ResearchBriefSignalClass.market_structure_sam: ("market_overview", "summary"),
    ResearchBriefSignalClass.strategic_wedge_candidates: ("summary",),
    ResearchBriefSignalClass.embedded_threats: ("competitive_landscape", "risks_and_uncertainties", "summary"),
    ResearchBriefSignalClass.buyer_process_friction: ("buyer_segments", "key_problems", "risks_and_uncertainties"),
    ResearchBriefSignalClass.gtm_motion_tradeoffs: ("buyer_segments", "competitive_landscape", "summary"),
    ResearchBriefSignalClass.proof_burden: ("buyer_segments", "key_problems", "risks_and_uncertainties"),
    ResearchBriefSignalClass.risk_classes: ("risks_and_uncertainties", "competitive_landscape"),
    ResearchBriefSignalClass.adoption_horizon: ("emerging_signals", "market_overview", "summary"),
    ResearchBriefSignalClass.competitive_landscape: ("competitive_landscape", "summary"),
    ResearchBriefSignalClass.emerging_signals: ("emerging_signals", "market_overview"),
    ResearchBriefSignalClass.key_problems: ("key_problems", "market_overview"),
}


# Scenario corpus reach-back allowed purposes when building or enriching a Strategy Brief (secondary input).
STRATEGY_BRIEF_CORPUS_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


# Payload keys downstream artifacts (message spine, asset plan, enablement, channel, collateral) should read.
DOWNSTREAM_CONSUMED_PAYLOAD_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "strategic_recommendation",
        "recommended_icp",
        "excluded_icps",
        "problem_frame",
        "wedge",
        "category_frame",
        "category_style",
        "differentiation_claim",
        "proof_requirements",
        "preferred_gtm_motion",
        "rejected_gtm_motions",
        "key_adoption_blockers",
        "strategic_risks",
        "assumptions",
        "decision_rationale",
        "dependent_message_requirements",
        "immediate_next_strategic_moves",
        "research_brief_divergence_notes",
    },
)


def assert_payload_matches_downstream_contract(payload: StrategyBriefStructuredPayload) -> None:
    """Validate payload shape for downstream consumers (raises ValidationError from Pydantic if invalid)."""
    StrategyBriefStructuredPayload.model_validate(payload.model_dump())


def validate_structured_payload_dict(data: dict[str, object]) -> StrategyBriefStructuredPayload:
    """Parse and validate a JSON/dict payload (e.g. future DB column or API body)."""
    return StrategyBriefStructuredPayload.model_validate(data)


def structured_payload_field_names() -> frozenset[str]:
    """All public scalar/list fields on the structured payload (excludes contract_version)."""
    return frozenset(DOWNSTREAM_CONSUMED_PAYLOAD_FIELDS)


# Legacy SQL columns on ``StrategyBrief`` (pre-contract); future generator may map new sections into these
# until a migration adds a JSON ``structured_decision_payload`` column.
LEGACY_STRATEGY_BRIEF_COLUMN_BY_CONCEPT: Final[dict[str, str]] = {
    "priority_icp": "icp_segmentation",
    "persona_model": "persona_model",
    "strategic_recommendation": "value_proposition",
    "category_positioning_decision": "positioning",
    "differentiation_logic": "competitive_strategy",
    "recommended_gtm_motion": "gtm_motion",
    "channel_execution": "channel_strategy",
    "growth_scaling": "growth_and_scaling",
    "strategic_risk_model": "strategy_risk_model",
    "strategic_risks": "risks_and_assumptions",
    "success_criteria": "success_metrics",
}