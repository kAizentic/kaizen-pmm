"""
Message Spine artifact contract (v1): narrative control layer after the Strategy Brief.

Defines human-facing section intent, the structured payload for downstream artifacts (asset plan,
enablement, channel, collateral, digital experience), primary inputs from the strategy decision
payload, and transformation boundaries.

Generation lives in the message-spine stage skill.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

MESSAGE_SPINE_CONTRACT_VERSION: Final[str] = "1.0"

TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Message Spine may: translate committed strategy into narrative hierarchy, prioritize messages "
    "by persona, define proof framing and objection handling, and set language guardrails. It may not: "
    "re-open core ICP, wedge, category frame, GTM motion, or strategic risk choices from the Strategy "
    "Brief; replace the structured_decision_payload as the source of truth; or substitute broad raw "
    "corpus or research-brief re-synthesis for those commitments. Bounded reach-back from research "
    "or scenario corpus is allowed only for proof, examples, competitor phrasing, or evidence recovery "
    "(see reachback_policy)."
)


class MessageSpineHumanSection(StrEnum):
    core_narrative = "core_narrative"
    category_statement = "category_statement"
    strategic_wedge_expression = "strategic_wedge_expression"
    value_pillars = "value_pillars"
    persona_message_hierarchy = "persona_message_hierarchy"
    proof_architecture = "proof_architecture"
    objection_skepticism_map = "objection_skepticism_map"
    messaging_guardrails = "messaging_guardrails"
    language_to_avoid = "language_to_avoid"
    content_angle_seeds = "content_angle_seeds"
    cta_action_logic = "cta_action_logic"


MESSAGE_SPINE_HUMAN_SECTION_ORDER: Final[tuple[MessageSpineHumanSection, ...]] = (
    MessageSpineHumanSection.core_narrative,
    MessageSpineHumanSection.category_statement,
    MessageSpineHumanSection.strategic_wedge_expression,
    MessageSpineHumanSection.value_pillars,
    MessageSpineHumanSection.persona_message_hierarchy,
    MessageSpineHumanSection.proof_architecture,
    MessageSpineHumanSection.objection_skepticism_map,
    MessageSpineHumanSection.messaging_guardrails,
    MessageSpineHumanSection.language_to_avoid,
    MessageSpineHumanSection.content_angle_seeds,
    MessageSpineHumanSection.cta_action_logic,
)

SECTION_INTENT: Final[dict[MessageSpineHumanSection, str]] = {
    MessageSpineHumanSection.core_narrative: "Single through-line story buyers should repeat; not a strategy re-decision.",
    MessageSpineHumanSection.category_statement: "How we name the company/product category for markets and sales.",
    MessageSpineHumanSection.strategic_wedge_expression: "Wedge expressed as narrative buyers can remember and defend.",
    MessageSpineHumanSection.value_pillars: "3–6 durable benefit pillars aligned to the committed strategy.",
    MessageSpineHumanSection.persona_message_hierarchy: "What each persona should hear first and which proof leads.",
    MessageSpineHumanSection.proof_architecture: "Proof points and ordering that support the story without bench noise.",
    MessageSpineHumanSection.objection_skepticism_map: "Likely skepticism and how messaging should acknowledge it.",
    MessageSpineHumanSection.messaging_guardrails: "Non-negotiable narrative rules inherited from strategy.",
    MessageSpineHumanSection.language_to_avoid: "Phrases and postures that undermine the chosen wedge or proof model.",
    MessageSpineHumanSection.content_angle_seeds: "Reusable hooks for campaigns and assets without re-deciding strategy.",
    MessageSpineHumanSection.cta_action_logic: "What we ask audiences to do next, consistent with GTM motion.",
}


class PersonaMessageFocus(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    persona: str = Field(..., min_length=2, description="Persona or audience slice label.")
    headline: str = Field(..., min_length=8, description="The first message this persona should hear.")
    supporting_proof: str = Field(
        default="",
        description="Which proof type or artifact to foreground for this persona.",
    )


class MessageSpineStructuredPayload(BaseModel):
    """Machine-readable narrative payload for downstream generators."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=MESSAGE_SPINE_CONTRACT_VERSION)

    master_narrative: str = Field(
        ...,
        min_length=24,
        description="Through-line story; must not contradict StrategyBriefStructuredPayload commitments.",
    )
    category_statement: str = Field(..., min_length=12, description="Category / what we are in market language.")
    wedge_expression: str = Field(..., min_length=8, description="Wedge as memorable buyer-facing expression.")
    value_pillars: list[str] = Field(..., min_length=2, description="Durable pillars tied to strategy.")
    persona_message_hierarchy: list[PersonaMessageFocus] = Field(
        ...,
        min_length=1,
        description="Ordered persona messaging; priority ICP first.",
    )
    proof_points: list[str] = Field(
        default_factory=list,
        description="Proof artifacts and claims sequencing for narrative support.",
    )
    objection_map: list[str] = Field(
        default_factory=list,
        description="Skepticism themes and how narrative should handle them.",
    )
    messaging_guardrails: list[str] = Field(
        default_factory=list,
        description="Rules every downstream artifact must preserve.",
    )
    forbidden_language: list[str] = Field(
        default_factory=list,
        description="Language and postures to avoid (hype, category soup, ICP sprawl, etc.).",
    )
    content_angle_seeds: list[str] = Field(
        default_factory=list,
        description="Campaign and asset hooks without re-opening strategy choices.",
    )
    cta_logic: list[str] = Field(
        default_factory=list,
        description="Calls-to-action and next steps aligned to GTM motion.",
    )
    downstream_asset_implications: list[str] = Field(
        ...,
        min_length=2,
        description="How asset plan, enablement, channel, and DX should consume this spine.",
    )
    strategy_brief_divergence_notes: str | None = Field(
        default=None,
        description="Echo strategy divergence notes when present; spine does not resolve them.",
    )

    @field_validator(
        "value_pillars",
        "proof_points",
        "objection_map",
        "messaging_guardrails",
        "forbidden_language",
        "content_angle_seeds",
        "cta_logic",
        "downstream_asset_implications",
        mode="before",
    )
    @classmethod
    def _coerce_str_lists(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


# Strategy Brief structured payload keys that primarily feed each message spine field (documentation).
STRATEGY_PAYLOAD_FIELD_FEEDS: Final[dict[str, tuple[str, ...]]] = {
    "master_narrative": ("strategic_recommendation", "problem_frame", "wedge"),
    "category_statement": ("category_frame",),
    "wedge_expression": ("wedge", "differentiation_claim"),
    "value_pillars": ("problem_frame", "differentiation_claim", "proof_requirements", "preferred_gtm_motion"),
    "persona_message_hierarchy": ("recommended_icp", "excluded_icps", "proof_requirements"),
    "proof_points": ("proof_requirements", "key_adoption_blockers", "strategic_risks"),
    "objection_map": ("key_adoption_blockers", "strategic_risks"),
    "messaging_guardrails": ("dependent_message_requirements", "decision_rationale"),
    "forbidden_language": ("rejected_gtm_motions", "excluded_icps"),
    "content_angle_seeds": ("dependent_message_requirements", "wedge", "differentiation_claim"),
    "cta_logic": ("preferred_gtm_motion", "immediate_next_strategic_moves", "rejected_gtm_motions"),
    "downstream_asset_implications": (
        "proof_requirements",
        "persona_message_hierarchy",
        "preferred_gtm_motion",
    ),
    "strategy_brief_divergence_notes": ("research_brief_divergence_notes",),
}

MESSAGE_SPINE_CORPUS_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES

DOWNSTREAM_CONSUMED_SPINE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "master_narrative",
        "category_statement",
        "wedge_expression",
        "value_pillars",
        "persona_message_hierarchy",
        "proof_points",
        "objection_map",
        "messaging_guardrails",
        "forbidden_language",
        "content_angle_seeds",
        "cta_logic",
        "downstream_asset_implications",
        "strategy_brief_divergence_notes",
    },
)


def validate_message_spine_payload_dict(data: dict[str, object]) -> MessageSpineStructuredPayload:
    return MessageSpineStructuredPayload.model_validate(data)


# Map contract concepts to existing message_spines table columns (no migration beyond JSON payload).
LEGACY_MESSAGE_SPINE_COLUMN_BY_CONCEPT: Final[dict[str, str]] = {
    "core_narrative": "core_problem",
    "category_statement": "positioning_statement",
    "strategic_wedge_expression": "differentiation_wedge",
    "value_pillars": "value_proposition",
    "persona_message_hierarchy": "primary_audience",
    "proof_architecture": "proof_themes",
    "objection_skepticism_map": "objection_themes",
    "messaging_guardrails": "messaging_guardrails",
    "language_to_avoid": "messaging_guardrails",
    "content_angle_seeds": "secondary_audiences",
    "cta_action_logic": "cta_themes",
}
