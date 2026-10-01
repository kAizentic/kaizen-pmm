"""Performance inputs spec structured contract."""

import pytest
from pydantic import ValidationError

from kaizen.performance_inputs_contract import (
    PERFORMANCE_INPUTS_CONTRACT_VERSION,
    PI_TRANSFORMATION_BOUNDARIES,
    PerformanceInputsStructuredPayload,
    PerformanceSignalEntry,
    PiAssetPlanReference,
    PiLeadingLagging,
    PiSignalLevel,
    PiSignalType,
    validate_performance_inputs_payload_dict,
)


def _entry(name: str = "Test signal name") -> PerformanceSignalEntry:
    return PerformanceSignalEntry(
        signal_name=name,
        signal_level=PiSignalLevel.strategy,
        signal_type=PiSignalType.hybrid,
        why_it_matters="Why this signal matters for validation.",
        source_layer="strategy_brief.structured_decision_payload",
        collection_method="CRM and interview sampling",
        owner="PMM",
        cadence="Monthly",
        leading_or_lagging=PiLeadingLagging.mixed,
        success_condition="Trend improves vs baseline",
        risk_condition="Sustained negative pattern",
    )


def test_contract_version() -> None:
    assert PERFORMANCE_INPUTS_CONTRACT_VERSION == "1.0"


def test_boundaries_non_empty() -> None:
    assert "may not" in PI_TRANSFORMATION_BOUNDARIES.lower()


def test_validate_roundtrip() -> None:
    p = PerformanceInputsStructuredPayload(
        measurement_goals=["Goal one"],
        strategic_success_signals=[_entry()],
        message_resonance_signals=[_entry("Message resonance signal")],
        asset_performance_signals=[_entry("Asset signal")],
        sales_progression_signals=[_entry("Sales signal")],
        channel_performance_signals=[_entry("Channel signal")],
        digital_experience_signals=[_entry("Digital signal")],
        risk_invalidation_signals=[_entry("Risk signal")],
        signal_owners=["PMM"],
        instrumentation_priorities=["Priority one"],
        asset_plan_reference=PiAssetPlanReference(
            asset_plan_id=1,
            prioritized_asset_sequence=["website_copy"],
        ),
    )
    data = p.model_dump(mode="json")
    out = validate_performance_inputs_payload_dict(data)
    assert out.contract_version == PERFORMANCE_INPUTS_CONTRACT_VERSION


def test_payload_forbids_extra_keys() -> None:
    p = PerformanceInputsStructuredPayload(
        measurement_goals=["g"],
        strategic_success_signals=[_entry()],
        message_resonance_signals=[_entry("Message layer signal")],
        asset_performance_signals=[_entry("Asset layer signal")],
        sales_progression_signals=[_entry("Sales layer signal")],
        channel_performance_signals=[_entry("Channel layer signal")],
        digital_experience_signals=[_entry("Digital layer signal")],
        risk_invalidation_signals=[_entry("Risk layer signal")],
        signal_owners=["o"],
        instrumentation_priorities=["p"],
        asset_plan_reference=PiAssetPlanReference(asset_plan_id=1, prioritized_asset_sequence=["x"]),
    )
    d = p.model_dump(mode="json")
    d["bogus"] = 1
    with pytest.raises(ValidationError):
        validate_performance_inputs_payload_dict(d)
