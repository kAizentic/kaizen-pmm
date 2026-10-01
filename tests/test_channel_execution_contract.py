"""Channel execution plan contract: versioned structured payload and execution-oriented sections."""

import pytest
from pydantic import ValidationError

from kaizen.channel_execution_contract import (
    CHANNEL_EXECUTION_CONTRACT_VERSION,
    CEP_HUMAN_SECTION_ORDER,
    CepAssetPlanReference,
    CepHumanSection,
    ChannelExecutionStructuredPayload,
    ChannelSupportingCollateralRef,
    PrioritizedChannelEntry,
    validate_channel_execution_payload_dict,
)


def test_contract_version_present():
    assert CHANNEL_EXECUTION_CONTRACT_VERSION
    assert CHANNEL_EXECUTION_CONTRACT_VERSION[0].isdigit()


def test_human_sections_execution_order():
    assert CEP_HUMAN_SECTION_ORDER[0] == CepHumanSection.channel_priorities
    assert CepHumanSection.deferred_channels in CEP_HUMAN_SECTION_ORDER


def test_payload_rejects_extra_keys():
    base = {
        "contract_version": CHANNEL_EXECUTION_CONTRACT_VERSION,
        "prioritized_channels": [
            {
                "channel_name": "Outbound / sequences",
                "priority_rank": 1,
                "objective": "Book qualified meetings with proof-first touches",
                "target_persona": "VP Eng",
                "buying_stage": "consideration",
                "message_emphasis": "Lead with wedge and proof ladder",
                "proof_needed": "Benchmark pack",
                "key_assets": ["proof_template"],
                "dependencies": [],
                "success_signal": "Replies cite proof assets",
            },
        ],
        "channel_roles": ["Outbound owns first touch"],
        "channel_message_map": ["**Outbound:** emphasize proof"],
        "channel_asset_map": ["**Outbound:** proof_template"],
        "sequencing_dependencies": ["Proof before scale"],
        "channel_proof_requirements": ["Outbound: SOC2-ready pack"],
        "channel_risks": ["Drift if messaging ignores spine"],
        "early_execution_recommendations": ["Launch outbound with proof_template"],
        "success_signals": ["SQL quality"],
        "deferred_channels": [],
        "supporting_collateral_refs": [],
        "asset_plan_reference": {
            "asset_plan_id": 1,
            "prioritized_asset_sequence": ["proof_template"],
            "proof_dependency_echo": [],
        },
        "message_spine_divergence_notes": None,
        "bogus": 1,
    }
    with pytest.raises(ValidationError):
        validate_channel_execution_payload_dict(base)


def test_minimal_valid_round_trip():
    ch = PrioritizedChannelEntry(
        channel_name="SEO / web / GEO discovery",
        priority_rank=2,
        objective="Capture demand-side language with proof-backed pages",
        target_persona="Practitioner",
        buying_stage="awareness",
        message_emphasis="Category + proof hooks from spine",
        proof_needed="Audit trail and latency proof",
        key_assets=["whitepaper", "website_copy"],
        dependencies=["proof_template"],
        success_signal="Organic sessions on pillar pages",
    )
    p = ChannelExecutionStructuredPayload(
        prioritized_channels=[ch],
        channel_roles=["SEO supports long-cycle education"],
        channel_message_map=["**SEO:** lead with searchable proof themes"],
        channel_asset_map=["**SEO:** whitepaper, website_copy"],
        sequencing_dependencies=["Publish proof_template before whitepaper scale"],
        channel_proof_requirements=["SEO: technical validation pages"],
        channel_risks=["GEO volatility on category queries"],
        early_execution_recommendations=["Index pillar pages after proof review"],
        success_signals=["Qualified organic clicks"],
        asset_plan_reference=CepAssetPlanReference(
            asset_plan_id=3,
            prioritized_asset_sequence=["proof_template", "whitepaper"],
            proof_dependency_echo=["Invoice cycle-time proof"],
        ),
    )
    d = p.model_dump(mode="json")
    out = validate_channel_execution_payload_dict(d)
    assert out.contract_version == CHANNEL_EXECUTION_CONTRACT_VERSION


def test_supporting_collateral_ref_optional_artifact_id():
    r = ChannelSupportingCollateralRef(
        collateral_type="one_pager",
        collateral_artifact_id=None,
        reference_note="ref",
    )
    assert r.collateral_artifact_id is None
