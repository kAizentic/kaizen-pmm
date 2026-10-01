"""Contracts for running golden regression checks as a suite."""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from kaizen.scenario_regression_contract import ScenarioRegressionPassStatus

SCENARIO_REGRESSION_SUITE_CONTRACT_VERSION: Final[str] = "1.0"


class ScenarioSuiteEntry(BaseModel):
    """One scenario in a regression suite."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scenario_id: int = Field(..., ge=1)
    scenario_title: str | None = Field(default=None, max_length=300)
    baseline_label: str = Field(..., min_length=1, max_length=120)
    expectation_profile: str | None = Field(default=None, max_length=120)
    expectation_file: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class ScenarioRegressionSuiteDefinition(BaseModel):
    """Filesystem JSON definition for a lightweight golden scenario suite."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=SCENARIO_REGRESSION_SUITE_CONTRACT_VERSION, max_length=16)
    suite_name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=1200)
    created_at: datetime
    entries: list[ScenarioSuiteEntry] = Field(default_factory=list)


class ScenarioSuiteEntryResult(BaseModel):
    """Aggregated compare/expectation result for one suite scenario."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scenario_id: int = Field(..., ge=1)
    scenario_title: str = Field(..., min_length=1, max_length=300)
    baseline_label: str = Field(..., min_length=1, max_length=120)
    compare_pass_status: ScenarioRegressionPassStatus
    expectation_pass_status: ScenarioRegressionPassStatus | None = None
    overall_pass_status: ScenarioRegressionPassStatus
    compare_summary: str = Field(default="", max_length=3000)
    expectation_summary: str | None = Field(default=None, max_length=3000)
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    invariant_failures: list[str] = Field(default_factory=list)
    protected_metric_failures: list[str] = Field(default_factory=list)
    unexpected_regressions: list[str] = Field(default_factory=list)


class ScenarioRegressionSuiteResult(BaseModel):
    """Top-level suite result for CLI/CI output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    suite_name: str = Field(..., min_length=1, max_length=120)
    evaluated_at: datetime
    overall_pass_status: ScenarioRegressionPassStatus
    total_scenarios: int = Field(..., ge=0)
    scenarios_passed: int = Field(..., ge=0)
    scenarios_failed: int = Field(..., ge=0)
    entry_results: list[ScenarioSuiteEntryResult] = Field(default_factory=list)
    summary: str = Field(default="", max_length=3000)

