"""Asset plan contract: planning-layer sections, strict payload, downstream field set."""

from kaizen.asset_plan_contract import (
    ASSET_PLAN_CONTRACT_VERSION,
    ASSET_PLAN_HUMAN_SECTION_ORDER,
    AssetPlanHumanSection,
    DOWNSTREAM_CONSUMED_ASSET_PLAN_FIELDS,
    TRANSFORMATION_BOUNDARIES,
    validate_asset_plan_payload_dict,
)


def test_contract_version_is_semverish():
    assert ASSET_PLAN_CONTRACT_VERSION
    parts = ASSET_PLAN_CONTRACT_VERSION.split(".")
    assert len(parts) >= 1


def test_human_section_enum_covers_planning_intent():
    names = {s.value for s in AssetPlanHumanSection}
    assert "planning_assumptions" in names
    assert "deferred_assets" in names
    assert ASSET_PLAN_HUMAN_SECTION_ORDER[0] == AssetPlanHumanSection.planning_assumptions


def test_transformation_boundaries_forbid_strategy_rewrite():
    low = TRANSFORMATION_BOUNDARIES.lower()
    assert "may not" in low
    assert "wedge" in low or "icp" in low


def test_downstream_consumed_fields_is_superset_of_core_lists():
    for key in (
        "prioritized_assets",
        "proof_dependencies",
        "downstream_channel_implications",
    ):
        assert key in DOWNSTREAM_CONSUMED_ASSET_PLAN_FIELDS


def test_validate_asset_plan_payload_dict_accepts_minimal_valid():
    data: dict[str, object] = {
        "planning_assumptions": ["Assumption: sequencing follows spine + strategy payloads."],
        "prioritized_assets": [
            {
                "asset_type": "one_pager",
                "target_persona": "Economic buyer",
                "buying_stage": "consideration",
                "channel": "email",
                "objective": "Map committed pain to measurable outcome",
                "message_job": "Carry category line from spine without reframing",
                "proof_required": "Named ROI or cycle-time proof",
                "production_effort": "low",
                "dependency_assets": [],
                "priority_rank": 1,
            },
        ],
        "asset_matrix": ["Economic buyer | consideration | email | one-pager | hero claim"],
        "proof_dependencies": ["Spine proof ladder item one"],
        "production_dependencies": [
            "Freeze narrative spine before scaling web claims",
            "Sequence deck after one-pager",
        ],
        "near_term_recommendations": ["Ship one-pager and proof checklist first"],
        "downstream_channel_implications": [
            "Collateral generators consume prioritized_assets order",
            "Channel spend respects deferred_assets when proof is thin",
        ],
    }
    p = validate_asset_plan_payload_dict(data)
    assert p.contract_version == ASSET_PLAN_CONTRACT_VERSION
    assert p.prioritized_assets[0].priority_rank == 1
