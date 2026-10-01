"""Message Spine contract: sections, payload shape, downstream field surface."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kaizen.message_spine_contract import (
    DOWNSTREAM_CONSUMED_SPINE_FIELDS,
    MESSAGE_SPINE_CONTRACT_VERSION,
    MESSAGE_SPINE_CORPUS_REACHBACK_ALLOWED,
    MESSAGE_SPINE_HUMAN_SECTION_ORDER,
    SECTION_INTENT,
    STRATEGY_PAYLOAD_FIELD_FEEDS,
    TRANSFORMATION_BOUNDARIES,
    MessageSpineHumanSection,
    MessageSpineStructuredPayload,
    PersonaMessageFocus,
    validate_message_spine_payload_dict,
)
from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES


def _minimal_spine_payload() -> dict[str, object]:
    return {
        "master_narrative": "We tell one story: proof-first payables control for mid-market finance teams.",
        "category_statement": "Accounts-payable control layer for cycle time and audit-ready outcomes.",
        "wedge_expression": "Lead with measured close-cycle proof, not headline benchmarks alone.",
        "value_pillars": ["Problem: invoices stuck in approval", "Proof: audit-grade validation"],
        "persona_message_hierarchy": [
            {"persona": "Platform owner", "headline": "Recover throughput without new hardware sprawl.", "supporting_proof": "Customer throughput audit"},
        ],
        "proof_points": ["Named security pack", "Repeatable ROI narrative"],
        "objection_map": ["Skepticism: benchmark games → pivot to deployable proof"],
        "messaging_guardrails": ["Never promise hardware portability not in strategy"],
        "forbidden_language": ["Generic TAM flex when SAM was committed"],
        "content_angle_seeds": ["Wedge-led case study", "Committee-ready proof ladder"],
        "cta_logic": ["Book proof review workshop", "Share audit template"],
        "downstream_asset_implications": ["Web: wedge above fold", "SEB: persona order from spine"],
        "strategy_brief_divergence_notes": None,
    }


def test_message_spine_human_sections_are_eleven_narrative_intents():
    assert len(MESSAGE_SPINE_HUMAN_SECTION_ORDER) == 11
    assert set(MESSAGE_SPINE_HUMAN_SECTION_ORDER) == set(MessageSpineHumanSection)
    for sec in MESSAGE_SPINE_HUMAN_SECTION_ORDER:
        assert len(SECTION_INTENT[sec]) >= 20


def test_structured_payload_strict_and_downstream_oriented():
    p = MessageSpineStructuredPayload.model_validate(_minimal_spine_payload())
    assert p.contract_version == MESSAGE_SPINE_CONTRACT_VERSION
    assert len(p.persona_message_hierarchy) >= 1
    assert isinstance(p.persona_message_hierarchy[0], PersonaMessageFocus)
    assert len(p.downstream_asset_implications) >= 2
    names = {f for f in DOWNSTREAM_CONSUMED_SPINE_FIELDS}
    for key in (
        "master_narrative",
        "proof_points",
        "objection_map",
        "forbidden_language",
        "downstream_asset_implications",
    ):
        assert key in names


def test_payload_rejects_unknown_keys():
    bad = _minimal_spine_payload()
    bad["noise_field"] = "nope"
    with pytest.raises(ValidationError):
        MessageSpineStructuredPayload.model_validate(bad)


def test_roundtrip_dict_helper():
    p = validate_message_spine_payload_dict(MessageSpineStructuredPayload.model_validate(_minimal_spine_payload()).model_dump(mode="json"))
    assert p.wedge_expression


def test_strategy_payload_feed_map_documents_primary_inputs():
    assert "master_narrative" in STRATEGY_PAYLOAD_FIELD_FEEDS
    assert "strategic_recommendation" in STRATEGY_PAYLOAD_FIELD_FEEDS["master_narrative"]


def test_transformation_boundaries_and_reachback_policy():
    low = TRANSFORMATION_BOUNDARIES.lower()
    assert "re-open" in low or "not" in low
    assert "corpus" in low or "reach" in low
    assert MESSAGE_SPINE_CORPUS_REACHBACK_ALLOWED == ALLOWED_REACHBACK_CATEGORIES
