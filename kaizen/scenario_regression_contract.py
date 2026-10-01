"""Contracts for golden-scenario evaluator regression checks."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

SCENARIO_REGRESSION_CONTRACT_VERSION: Final[str] = "1.0"


class ScenarioRegressionPassStatus(StrEnum):
    passed = "passed"
    failed = "failed"


class ScenarioProtectedInvariantType(StrEnum):
    must_not_change_overall_verdict_to_worse = "must_not_change_overall_verdict_to_worse"
    must_not_reintroduce_structured_gap_in_buying_trigger = "must_not_reintroduce_structured_gap_in_buying_trigger"
    must_not_reintroduce_structured_gap_in_positioning = "must_not_reintroduce_structured_gap_in_positioning"
    must_not_increase_contradiction_count = "must_not_increase_contradiction_count"
    must_not_drop_spine_below = "must_not_drop_spine_below"
    must_keep_headers_mostly_clean = "must_keep_headers_mostly_clean"


class ScenarioProtectedInvariant(BaseModel):
    """One explicit, inspectable invariant for a golden scenario."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    invariant_type: ScenarioProtectedInvariantType
    enabled: bool = True
    threshold: float | None = None
    notes: str | None = Field(default=None, max_length=600)


class ScenarioRegressionKeyMetrics(BaseModel):
    """Normalized evaluator fields used by regression gates."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    overall_score: float | None = None
    research_normalization_score: float | None = None
    strategic_spine_score: float | None = None
    strategy_cohesion_score: float | None = None
    downstream_artifacts_score: float | None = None
    header_cleanliness_score: float | None = None
    contamination_score: float | None = None
    duplication_score: float | None = None
    wedge_correctness: float | None = None
    positioning_correctness: float | None = None
    buying_trigger_correctness: float | None = None
    competitor_loss_completeness: float | None = None
    contradiction_count: int | None = None
    missing_link_count: int | None = None
    redundancy_count: int | None = None
    overall_verdict: str | None = None
    operator_primary_blocker: str | None = None

    # Optional observability for invariants when raw header fields are available.
    strategic_wedge: str | None = None
    positioning: str | None = None
    why_competitors_lose: str | None = None
    buying_trigger: str | None = None


class ScenarioRegressionThresholds(BaseModel):
    """Optional per-metric tolerated regression bounds."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    max_overall_score_drop: float | None = None
    max_research_score_drop: float | None = None
    max_spine_score_drop: float | None = None
    max_cohesion_score_drop: float | None = None
    max_downstream_score_drop: float | None = None
    max_duplication_score_drop: float | None = None
    max_positioning_drop: float | None = None
    max_trigger_drop: float | None = None
    max_competitor_drop: float | None = None
    max_new_contradictions: int | None = None
    max_new_missing_links: int | None = None
    max_new_redundancy: int | None = None


class ScenarioRegressionBaseline(BaseModel):
    """Stored golden-scenario baseline."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SCENARIO_REGRESSION_CONTRACT_VERSION, max_length=16)
    scenario_id: int = Field(..., ge=1)
    scenario_title: str = Field(..., min_length=1, max_length=300)
    baseline_label: str = Field(..., min_length=1, max_length=120)
    recorded_at: datetime
    evaluator_summary: dict[str, Any] = Field(default_factory=dict)
    key_metrics: ScenarioRegressionKeyMetrics
    thresholds: ScenarioRegressionThresholds = Field(default_factory=ScenarioRegressionThresholds)
    protected_invariants: list[ScenarioProtectedInvariant] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class ScenarioRegressionResult(BaseModel):
    """Comparison result between a current evaluator payload and a stored baseline."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scenario_id: int = Field(..., ge=1)
    scenario_title: str = Field(..., min_length=1, max_length=300)
    baseline_label: str = Field(..., min_length=1, max_length=120)
    compared_at: datetime
    pass_status: ScenarioRegressionPassStatus
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    invariant_failures: list[str] = Field(default_factory=list)
    metric_deltas: dict[str, float | int] = Field(default_factory=dict)
    baseline_metrics: ScenarioRegressionKeyMetrics | None = None
    current_metrics: ScenarioRegressionKeyMetrics | None = None
    summary: str = Field(default="", max_length=3000)

