"""Digital experience structured contract: strict payload shape."""

import pytest
from pydantic import ValidationError

from kaizen.digital_experience_contract import (
    DIGITAL_EXPERIENCE_CONTRACT_VERSION,
    DX_TRANSFORMATION_BOUNDARIES,
    DigitalExperienceStructuredPayload,
    PrioritizedSurfaceEntry,
    validate_digital_experience_payload_dict,
)


def test_contract_version_is_stable() -> None:
    assert DIGITAL_EXPERIENCE_CONTRACT_VERSION == "1.0"


def test_transformation_boundaries_non_empty() -> None:
    assert "may not" in DX_TRANSFORMATION_BOUNDARIES.lower()


def test_validate_digital_experience_payload_dict_roundtrip() -> None:
    p = DigitalExperienceStructuredPayload(
        experience_goals=["Advance proof-first digital evaluation."],
        prioritized_surfaces=[
            PrioritizedSurfaceEntry(
                surface_name="Home / primary digital entry",
                priority_rank=1,
                objective="Establish category and primary proof narrative for the coalition.",
                target_persona="Platform engineering lead",
                buying_stage="awareness",
                primary_message="Cycle-time and close-speed story without generic automation claims.",
                supporting_proof="Named metrics and audit posture from strategy proof requirements.",
                primary_cta="Request technical walkthrough",
                secondary_cta="Download architecture overview",
                linked_assets=["website_copy"],
            ),
        ],
        page_role_map=["Home: trust + category clarity"],
        page_narrative_map=["Home: spine-aligned headline and proof band"],
        cta_hierarchy=["Primary evaluation CTA after proof consumption"],
        proof_module_map=["Home: proof band tied to asset plan"],
        trust_module_map=["Coalition-specific trust slots"],
        persona_routing_logic=["Route infra readers to technical proof modules"],
        asset_embedding_map=["Embed planned assets per asset plan sequence"],
        reusable_modules=["hero_category_proof"],
        friction_reduction_rules=["Address procurement security path early"],
        early_implementation_recommendations=["Launch home + product with linked proof assets"],
        asset_plan_reference={
            "asset_plan_id": 1,
            "prioritized_asset_sequence": ["website_copy"],
        },
    )
    data = p.model_dump(mode="json")
    out = validate_digital_experience_payload_dict(data)
    assert out.contract_version == DIGITAL_EXPERIENCE_CONTRACT_VERSION


def test_payload_forbids_unknown_top_level_keys() -> None:
    base = DigitalExperienceStructuredPayload(
        experience_goals=["g"],
        prioritized_surfaces=[
            PrioritizedSurfaceEntry(
                surface_name="Home / primary digital entry",
                priority_rank=1,
                objective="Objective text here for validation.",
                target_persona="Buyer",
                buying_stage="stage",
                primary_message="Primary message line for page.",
                supporting_proof="proof",
                primary_cta="Primary CTA",
                linked_assets=["x"],
            ),
        ],
        page_role_map=["r"],
        page_narrative_map=["n"],
        cta_hierarchy=["c"],
        proof_module_map=["p"],
        trust_module_map=["t"],
        persona_routing_logic=["pr"],
        asset_embedding_map=["ae"],
        reusable_modules=["rm"],
        friction_reduction_rules=["f"],
        early_implementation_recommendations=["e"],
        asset_plan_reference={"asset_plan_id": 1, "prioritized_asset_sequence": ["a"]},
    )
    d = base.model_dump(mode="json")
    d["extra_field"] = "nope"
    with pytest.raises(ValidationError):
        validate_digital_experience_payload_dict(d)
