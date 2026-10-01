"""Performance Review contract: enums, payload validation, transformation boundaries text."""

from kaizen.performance_review_contract import (
    PR_TRANSFORMATION_BOUNDARIES,
    PERFORMANCE_REVIEW_CONTRACT_VERSION,
    PerformanceInputsSpecReference,
    PerformanceReviewStructuredPayload,
    PrActionRecommendation,
    PrConfidence,
    PrObservedStatus,
    ReviewAssessmentEntry,
    validate_performance_review_payload_dict,
)


def test_contract_version_and_boundaries_are_stable():
    assert PERFORMANCE_REVIEW_CONTRACT_VERSION == "1.0"
    assert "interpret" in PR_TRANSFORMATION_BOUNDARIES.lower()
    assert "dashboard" in PR_TRANSFORMATION_BOUNDARIES.lower()
    assert "performance inputs spec" in PR_TRANSFORMATION_BOUNDARIES.lower() or "measurement" in PR_TRANSFORMATION_BOUNDARIES.lower()


def test_validate_performance_review_payload_dict_round_trip():
    entry = ReviewAssessmentEntry(
        signal_name="Test strategic signal name",
        observed_status=PrObservedStatus.mixed,
        interpretation="Interpretation meets minimum length for contract.",
        likely_implication="Implication meets minimum length for contract.",
        confidence=PrConfidence.medium,
        action_recommendation=PrActionRecommendation.investigate,
    )
    p = PerformanceReviewStructuredPayload(
        review_scope="Review scope string long enough for validation rules here.",
        signal_coverage=["coverage line one", "coverage line two"],
        strategic_validation_assessment=[entry],
        message_resonance_assessment=[entry],
        asset_performance_assessment=[entry],
        sales_progression_assessment=[entry],
        channel_execution_assessment=[entry],
        digital_experience_assessment=[entry],
        risk_invalidation_assessment=[entry],
        recommended_adjustments=["Do a thing"],
        hold_steady_areas=["Hold a thing"],
        data_gaps=["Gap one"],
        next_instrumentation_needs=["Need one"],
        performance_inputs_reference=PerformanceInputsSpecReference(
            performance_inputs_spec_id=1,
            performance_inputs_contract_version="1.0",
            operational_input_row_count=0,
            measurement_goal_count=1,
        ),
    )
    d = p.model_dump(mode="json")
    again = validate_performance_review_payload_dict(d)
    assert again.contract_version == PERFORMANCE_REVIEW_CONTRACT_VERSION


def test_enum_values_are_stable_strings():
    assert PrObservedStatus.insufficient_data.value == "insufficient_data"
    assert PrActionRecommendation.escalate.value == "escalate"
