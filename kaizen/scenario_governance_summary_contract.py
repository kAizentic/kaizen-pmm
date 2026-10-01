"""
Scenario-level governance summary: aggregated PMM health for operator visibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

SCENARIO_GOVERNANCE_SUMMARY_CONTRACT_VERSION: Final[str] = "1.0"


class GovernanceSummaryStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    blocked = "blocked"
    incomplete = "incomplete"


class GovernanceRecommendedNextAction(StrEnum):
    regenerate_research_brief = "regenerate_research_brief"
    approve_research_brief = "approve_research_brief"
    resolve_positioning_conflict = "resolve_positioning_conflict"
    approve_pmm_before_collateral = "approve_pmm_before_collateral"
    resolve_pmm_blocked_status = "resolve_pmm_blocked_status"
    generate_missing_messaging_brief = "generate_missing_messaging_brief"
    review_cross_artifact_contradiction = "review_cross_artifact_contradiction"
    review_low_quality_one_pager = "review_low_quality_one_pager"
    review_low_quality_messaging_brief = "review_low_quality_messaging_brief"
    review_low_quality_channel_plan = "review_low_quality_channel_plan"
    safe_to_proceed_operator_review = "safe_to_proceed_operator_review"


class GovernanceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(..., min_length=2, max_length=64)
    artifact_type: str | None = Field(default=None, max_length=64)
    artifact_id: int | None = None
    detail: str = Field(default="", max_length=1200)


class GovernanceBlockingIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(..., min_length=2, max_length=80)
    message: str = Field(..., min_length=4, max_length=1200)
    severity: str = Field(default="high", max_length=32)


class GovernanceWarning(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(..., min_length=2, max_length=80)
    message: str = Field(..., min_length=4, max_length=1200)


class ArtifactGovernanceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_type: str = Field(..., min_length=4, max_length=64)
    exists: bool = False
    structured: bool = False
    latest_id: int | None = None
    latest_status: str | None = Field(default=None, max_length=32)
    quality_pass: bool | None = None
    quality_overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rewrite_applied: bool = False
    normalization_applied: bool = False
    critical_warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class ScenarioGovernanceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SCENARIO_GOVERNANCE_SUMMARY_CONTRACT_VERSION, max_length=16)
    scenario_id: int = Field(..., ge=1)
    strategy_brief_id: int | None = Field(default=None, description="Scope filter used when building this summary.")

    research_status: str = Field(default="missing", max_length=32)
    canonical_assertion_status: str = Field(default="absent", max_length=32)
    approved_pmm_strategy_status: str = Field(default="missing", max_length=32)
    approved_pmm_strategy_version: str | None = Field(default=None, max_length=32)
    coherence_status: str = Field(default="absent", max_length=32)
    coherence_score: float | None = Field(default=None, ge=0.0, le=1.0)

    artifact_inventory: list[ArtifactGovernanceStatus] = Field(default_factory=list)
    artifact_quality_statuses: dict[str, str] = Field(default_factory=dict)
    cross_artifact_consistency_status: str = Field(default="not_evaluated", max_length=32)
    cross_artifact_consistency_score: float | None = Field(default=None, ge=0.0, le=1.0)

    rewrite_events: list[GovernanceEvent] = Field(default_factory=list)
    normalization_events: list[GovernanceEvent] = Field(default_factory=list)
    blocking_issues: list[GovernanceBlockingIssue] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    warnings: list[GovernanceWarning] = Field(default_factory=list)

    recommended_next_action: GovernanceRecommendedNextAction = Field(
        default=GovernanceRecommendedNextAction.safe_to_proceed_operator_review,
    )
    recommended_next_action_reason: str = Field(default="", max_length=1600)

    summary_status: GovernanceSummaryStatus = Field(default=GovernanceSummaryStatus.incomplete)
    generated_at: datetime = Field(..., description="UTC timestamp when summary was computed.")


def validate_scenario_governance_summary_dict(data: dict[str, object]) -> ScenarioGovernanceSummary:
    return ScenarioGovernanceSummary.model_validate(data)
