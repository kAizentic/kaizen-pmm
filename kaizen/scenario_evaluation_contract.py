"""
Scenario evaluation contract for run-to-run PMM quality tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

SCENARIO_EVALUATION_CONTRACT_VERSION: Final[str] = "1.0"


class EvaluationStatus(StrEnum):
    pass_ok = "pass"
    degraded = "degraded"
    fail = "fail"
    incomplete = "incomplete"


class EvaluationReadiness(StrEnum):
    ready = "ready"
    not_ready = "not_ready"
    review_required = "review_required"


class OverallVerdict(StrEnum):
    improving_but_blocked = "improving_but_blocked"
    blocked_upstream = "blocked_upstream"
    blocked_strategy_spine = "blocked_strategy_spine"
    downstream_only_healthy = "downstream_only_healthy"
    ready_for_broader_testing = "ready_for_broader_testing"
    ready_for_new_scenario = "ready_for_new_scenario"
    incomplete = "incomplete"


class ResearchNormalizationEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: EvaluationStatus
    score: float = Field(..., ge=0.0, le=1.0)
    header_cleanliness_score: float = Field(..., ge=0.0, le=1.0)
    contamination_score: float = Field(..., ge=0.0, le=1.0)
    duplication_score: float = Field(..., ge=0.0, le=1.0)
    malformed_synthesis_score: float = Field(..., ge=0.0, le=1.0)
    notable_failures: list[str] = Field(default_factory=list)
    notable_successes: list[str] = Field(default_factory=list)


class StrategicSpineEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: EvaluationStatus
    score: float = Field(..., ge=0.0, le=1.0)
    wedge_correctness: float = Field(..., ge=0.0, le=1.0)
    positioning_correctness: float = Field(..., ge=0.0, le=1.0)
    buying_trigger_correctness: float = Field(..., ge=0.0, le=1.0)
    competitor_loss_completeness: float = Field(..., ge=0.0, le=1.0)
    icp_precision: float = Field(..., ge=0.0, le=1.0)
    notable_failures: list[str] = Field(default_factory=list)
    notable_successes: list[str] = Field(default_factory=list)


class StrategyCohesionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: EvaluationStatus
    score: float = Field(..., ge=0.0, le=1.0)
    coherence_score: float = Field(..., ge=0.0, le=1.0)
    contradiction_count: int = Field(default=0, ge=0)
    missing_link_count: int = Field(default=0, ge=0)
    redundancy_count: int = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)


class DownstreamArtifactsEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: EvaluationStatus
    score: float = Field(..., ge=0.0, le=1.0)
    one_pager_quality: float = Field(..., ge=0.0, le=1.0)
    messaging_brief_quality: float = Field(..., ge=0.0, le=1.0)
    channel_execution_quality: float = Field(..., ge=0.0, le=1.0)
    cross_artifact_consistency_score: float = Field(..., ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class GovernanceStateEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary_status: str = Field(default="incomplete", max_length=32)
    blocking_issue_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    recommended_next_action: str = Field(default="", max_length=128)
    missing_core_artifacts: list[str] = Field(default_factory=list)


class OperatorVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    primary_blocker: str = Field(default="", max_length=400)
    should_continue_tuning_headers: bool = True
    should_continue_tuning_research_synthesis: bool = True
    should_continue_tuning_downstream: bool = True
    ready_for_new_scenario: bool = False
    readiness: EvaluationReadiness = EvaluationReadiness.review_required
    rationale: str = Field(default="", max_length=2000)


class EvaluationComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    previous_evaluation_score: float = Field(..., ge=0.0, le=1.0)
    delta_overall_score: float
    delta_research_normalization: float
    delta_strategic_spine: float
    delta_strategy_cohesion: float
    delta_downstream_artifacts: float
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)


class ScenarioEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SCENARIO_EVALUATION_CONTRACT_VERSION, max_length=16)
    scenario_id: int = Field(..., ge=1)
    scenario_title: str = Field(..., min_length=1, max_length=300)
    evaluated_at: datetime
    evaluation_run_label: str | None = Field(default=None, max_length=120)
    overall_verdict: OverallVerdict
    overall_score: float = Field(..., ge=0.0, le=1.0)
    summary: str = Field(default="", max_length=3000)

    research_normalization: ResearchNormalizationEvaluation
    strategic_spine: StrategicSpineEvaluation
    strategy_cohesion: StrategyCohesionEvaluation
    downstream_artifacts: DownstreamArtifactsEvaluation
    governance_state: GovernanceStateEvaluation
    operator_verdict: OperatorVerdict
    comparison: EvaluationComparison | None = None


def validate_scenario_evaluation_result_dict(data: dict[str, object]) -> ScenarioEvaluationResult:
    return ScenarioEvaluationResult.model_validate(data)

