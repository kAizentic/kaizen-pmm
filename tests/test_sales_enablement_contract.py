"""Sales enablement contract: versioned structured payload and deal-execution section model."""

import pytest
from pydantic import ValidationError

from kaizen.sales_enablement_contract import (
    SALES_ENABLEMENT_CONTRACT_VERSION,
    SEB_HUMAN_SECTION_ORDER,
    SebHumanSection,
    SalesEnablementStructuredPayload,
    CoalitionBuyerEntry,
    SebAssetPlanReference,
    SupportingCollateralRef,
    validate_sales_enablement_payload_dict,
)


def test_contract_version_is_semantic_string():
    assert SALES_ENABLEMENT_CONTRACT_VERSION
    assert "." in SALES_ENABLEMENT_CONTRACT_VERSION or SALES_ENABLEMENT_CONTRACT_VERSION.isdigit()


def test_human_sections_are_deal_execution_ordered():
    keys = list(SEB_HUMAN_SECTION_ORDER)
    assert keys[0] == SebHumanSection.deal_narrative
    assert SebHumanSection.buyer_coalition in keys
    assert SebHumanSection.next_step_assets in keys
    assert keys[-1] == SebHumanSection.deal_progression


def test_structured_payload_rejects_unknown_keys():
    base = {
        "contract_version": SALES_ENABLEMENT_CONTRACT_VERSION,
        "deal_narrative": "x" * 30,
        "buyer_coalition": [
            {
                "role": "CTO",
                "priority": "lead",
                "cares_about": "velocity",
                "fears": "",
                "proof_they_need": "benchmark",
            },
        ],
        "lead_buyer": "CTO",
        "win_over_buyers": [],
        "discovery_questions": ["q1", "q2", "q3"],
        "proof_requirements": ["p1"],
        "objection_map": ["o1"],
        "competitive_traps": ["t1"],
        "qualification_signals": ["qual"],
        "disqualification_signals": ["dis"],
        "next_step_assets": ["a1"],
        "deal_progression_guidance": "next thirty days",
        "supporting_collateral_refs": [],
        "asset_plan_reference": {
            "asset_plan_id": 1,
            "prioritized_asset_sequence": ["proof_template"],
            "proof_dependency_echo": [],
        },
        "message_spine_divergence_notes": None,
        "extra_field": "nope",
    }
    with pytest.raises(ValidationError):
        validate_sales_enablement_payload_dict(base)


def test_validate_round_trip_minimal_payload():
    p = SalesEnablementStructuredPayload(
        deal_narrative="Deal story anchored on approved spine and strategy." * 2,
        buyer_coalition=[
            CoalitionBuyerEntry(
                role="VP Eng",
                priority="lead",
                cares_about="Ship velocity without regressions",
            ),
        ],
        lead_buyer="VP Eng",
        discovery_questions=["Who signs?", "What proof bar?", "Procurement path?"],
        proof_requirements=["Security review pack"],
        objection_map=["Latency concern → latency proof from plan"],
        competitive_traps=["Trap: sounding like a feature add-on"],
        qualification_signals=["ICP: enterprise platform teams"],
        disqualification_signals=["No budget owner"],
        next_step_assets=["1. **proof_template** — stage: evaluation"],
        deal_progression_guidance="Sequence proof before scale narrative.",
        asset_plan_reference=SebAssetPlanReference(
            asset_plan_id=9,
            prioritized_asset_sequence=["proof_template", "sales_deck"],
            proof_dependency_echo=["SOC2 summary"],
        ),
    )
    d = p.model_dump(mode="json")
    out = validate_sales_enablement_payload_dict(d)
    assert out.contract_version == SALES_ENABLEMENT_CONTRACT_VERSION


def test_supporting_collateral_ref_optional_id():
    r = SupportingCollateralRef(collateral_type="one_pager", collateral_artifact_id=None, reference_note="ref")
    assert r.collateral_artifact_id is None
