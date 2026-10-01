"""Contracts for pass-level blast-radius expectations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from kaizen.scenario_regression_contract import ScenarioRegressionPassStatus

SCENARIO_REGRESSION_EXPECTATION_CONTRACT_VERSION: Final[str] = "1.0"


class MetricDirection(StrEnum):
    higher_is_better = "higher_is_better"
    lower_is_better = "lower_is_better"
    categorical = "categorical"


class IntendedImprovement(BaseModel):
    """Metric expected to improve, or at least hold if configured."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_name: str = Field(..., min_length=1, max_length=120)
    minimum_delta: float | int | None = None
    improve_or_hold: bool = True
    tolerance: float | int = 0.0
    direction: MetricDirection | None = None
    notes: str | None = Field(default=None, max_length=600)


class ProtectedMetric(BaseModel):
    """Metric outside the intended blast radius that must not regress."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_name: str = Field(..., min_length=1, max_length=120)
    max_allowed_regression: float | int = 0.0
    direction: MetricDirection | None = None
    notes: str | None = Field(default=None, max_length=600)


class AllowedRegression(BaseModel):
    """Narrow, explicit tolerated movement for this pass."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_name: str = Field(..., min_length=1, max_length=120)
    max_allowed_regression: float | int
    direction: MetricDirection | None = None
    reason: str = Field(..., min_length=1, max_length=800)


class ScenarioBlastRadiusExpectation(BaseModel):
    """Operator-declared expected blast radius for one development pass."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SCENARIO_REGRESSION_EXPECTATION_CONTRACT_VERSION, max_length=16)
    expectation_label: str = Field(..., min_length=1, max_length=120)
    scenario_id: int = Field(..., ge=1)
    description: str = Field(default="", max_length=1200)
    created_at: datetime
    intended_improvements: list[IntendedImprovement] = Field(default_factory=list)
    protected_metrics: list[ProtectedMetric] = Field(default_factory=list)
    allowed_regressions: list[AllowedRegression] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class ScenarioBlastRadiusResult(BaseModel):
    """Result of matching observed deltas against the declared pass intent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expectation_label: str = Field(..., min_length=1, max_length=120)
    scenario_id: int = Field(..., ge=1)
    evaluated_at: datetime
    pass_status: ScenarioRegressionPassStatus
    intended_improvements_met: list[str] = Field(default_factory=list)
    protected_metric_failures: list[str] = Field(default_factory=list)
    allowed_regressions_observed: list[str] = Field(default_factory=list)
    unexpected_regressions: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=3000)

