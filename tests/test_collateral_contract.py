"""Typed collateral framework and One-Pager contract."""

from kaizen.collateral_contract import (
    COLLATERAL_FRAMEWORK_VERSION,
    ONE_PAGER_CONTRACT_VERSION,
    ONE_PAGER_HUMAN_SECTION_ORDER,
    ONE_PAGER_PROOF_RULES,
    ONE_PAGER_TRANSFORMATION_BOUNDARIES,
    SHARED_COLLATERAL_TRANSFORMATION_BOUNDARIES,
    TYPED_COLLATERAL_IMPLEMENTED,
    CollateralArtifactTypeKey,
    OnePagerHumanSection,
    validate_one_pager_payload_dict,
)


def test_framework_version_constants():
    assert COLLATERAL_FRAMEWORK_VERSION
    assert ONE_PAGER_CONTRACT_VERSION


def test_shared_boundaries_forbid_strategy_reopen():
    low = SHARED_COLLATERAL_TRANSFORMATION_BOUNDARIES.lower()
    assert "may not" in low
    assert "wedge" in low or "icp" in low


def test_one_pager_boundaries_enforce_compression():
    assert "whitepaper" in ONE_PAGER_TRANSFORMATION_BOUNDARIES.lower()


def test_proof_rules_cap_highlights():
    assert "three" in ONE_PAGER_PROOF_RULES.lower()


def test_registry_includes_legacy_and_future_stubs():
    assert CollateralArtifactTypeKey.one_pager == "one_pager"
    assert CollateralArtifactTypeKey.messaging_brief == "messaging_brief"
    assert CollateralArtifactTypeKey.solution_brief == "solution_brief"
    assert "one_pager" in TYPED_COLLATERAL_IMPLEMENTED
    assert "messaging_brief" in TYPED_COLLATERAL_IMPLEMENTED


def test_one_pager_human_section_order():
    assert OnePagerHumanSection.headline_category == ONE_PAGER_HUMAN_SECTION_ORDER[0]
    assert ONE_PAGER_HUMAN_SECTION_ORDER[-1] == OnePagerHumanSection.cta


def test_validate_one_pager_payload_minimal():
    d: dict[str, object] = {
        "target_persona": "CFO",
        "buying_stage": "consideration",
        "channel": "email",
        "headline": "Headline for enterprise buyers here",
        "category_line": "Control plane category line",
        "problem_statement": "Problem statement with enough length here.",
        "urgency_statement": "Urgency statement with enough length here.",
        "product_definition": "Product definition with enough length.",
        "differentiators": ["Diff one", "Diff two"],
        "proof_highlights": ["Proof one"],
        "target_buyer_summary": "Economic buyer in ICP segment",
        "buying_trigger": "Procurement and proof gate pressure",
        "cta": "Book a working session with solutions engineering.",
        "asset_plan_reference": {
            "asset_plan_id": 3,
            "priority_rank": 2,
            "planning_objective": "Leave-behind mapping pain to outcome",
            "message_job": "Carry category line from spine",
            "proof_required_from_plan": "Named ROI study",
            "dependency_assets": ["executive_brief"],
        },
    }
    p = validate_one_pager_payload_dict(d)
    assert p.collateral_type == "one_pager"
    assert p.asset_plan_reference.asset_plan_id == 3
