"""
Channel Execution Plan contract: channel-orchestration layer after Strategy, Spine, Asset Plan, and SEB.

Consumes structured payloads from those artifacts; typed collateral rows are supporting references only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kaizen.artifact_quality_contract import ChannelPlanQualityReport
from kaizen.cross_artifact_consistency_contract import CrossArtifactConsistencyReport
from kaizen.reachback_policy import ALLOWED_REACHBACK_CATEGORIES, ReachBackCategory

CHANNEL_EXECUTION_CONTRACT_VERSION: Final[str] = "1.2"

CEP_TRANSFORMATION_BOUNDARIES: Final[str] = (
    "The Channel Execution Plan may: prioritize channels, assign roles and objectives, map messages and planned "
    "assets by channel, define sequencing and proof needs per channel, name channel blockers and success signals, "
    "and defer lower-fit channels. It may not: rewrite strategy, invent a wedge or ICP, replace the asset plan as "
    "the source of production truth, become a generic channel wishlist, or substitute raw corpus synthesis for "
    "upstream structured payloads."
)

CEP_BOUNDED_REACHBACK_ALLOWED: Final[frozenset[ReachBackCategory]] = ALLOWED_REACHBACK_CATEGORIES


class CepHumanSection(StrEnum):
    channel_priorities = "channel_priorities"
    channel_roles = "channel_roles"
    channel_message_emphasis = "channel_message_emphasis"
    channel_asset_mapping = "channel_asset_mapping"
    sequencing_dependencies = "sequencing_dependencies"
    channel_proof = "channel_proof"
    channel_risks = "channel_risks"
    early_execution = "early_execution"
    success_signals = "success_signals"
    deferred_channels = "deferred_channels"


CEP_HUMAN_SECTION_ORDER: Final[tuple[CepHumanSection, ...]] = (
    CepHumanSection.channel_priorities,
    CepHumanSection.channel_roles,
    CepHumanSection.channel_message_emphasis,
    CepHumanSection.channel_asset_mapping,
    CepHumanSection.sequencing_dependencies,
    CepHumanSection.channel_proof,
    CepHumanSection.channel_risks,
    CepHumanSection.early_execution,
    CepHumanSection.success_signals,
    CepHumanSection.deferred_channels,
)


class PrioritizedChannelEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channel_name: str = Field(..., min_length=3)
    priority_rank: int = Field(..., ge=1, le=99)
    objective: str = Field(..., min_length=8)
    target_persona: str = Field(..., min_length=2)
    buying_stage: str = Field(..., min_length=3)
    message_emphasis: str = Field(..., min_length=8)
    proof_needed: str = Field(..., min_length=4)
    key_assets: list[str] = Field(..., min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    success_signal: str = Field(..., min_length=8)

    @field_validator("key_assets", "dependencies", mode="before")
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


class ChannelSupportingCollateralRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    collateral_type: str = Field(..., min_length=2)
    collateral_artifact_id: int | None = Field(default=None, ge=1)
    reference_note: str = Field(
        default="",
        description="Supporting reference only; which channels can use this artifact.",
    )


class CepAssetPlanReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_plan_id: int = Field(..., ge=1)
    prioritized_asset_sequence: list[str] = Field(..., min_length=1)
    proof_dependency_echo: list[str] = Field(default_factory=list)


class ChannelExecutionStructuredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = Field(default=CHANNEL_EXECUTION_CONTRACT_VERSION)
    prioritized_channels: list[PrioritizedChannelEntry] = Field(..., min_length=1)
    channel_roles: list[str] = Field(..., min_length=1)
    channel_message_map: list[str] = Field(
        ...,
        min_length=1,
        description="Per-channel narrative emphasis lines (machine + human readable).",
    )
    channel_asset_map: list[str] = Field(..., min_length=1)
    sequencing_dependencies: list[str] = Field(..., min_length=1)
    channel_proof_requirements: list[str] = Field(..., min_length=1)
    channel_risks: list[str] = Field(..., min_length=1)
    early_execution_recommendations: list[str] = Field(..., min_length=1)
    success_signals: list[str] = Field(..., min_length=1)
    deferred_channels: list[str] = Field(default_factory=list)
    supporting_collateral_refs: list[ChannelSupportingCollateralRef] = Field(default_factory=list)
    asset_plan_reference: CepAssetPlanReference
    message_spine_divergence_notes: str | None = None
    quality_report: ChannelPlanQualityReport | None = Field(
        default=None,
        description="Primary channel row artifact quality (observability).",
    )
    rewrite_applied: bool = Field(default=False)
    rewrite_reason: str | None = Field(default=None, max_length=800)
    cross_artifact_consistency_report: CrossArtifactConsistencyReport | None = Field(
        default=None,
        description="Cross-artifact consistency when evaluated with peer payloads.",
    )
    cross_artifact_normalization_applied: bool = Field(default=False)
    cross_artifact_normalization_reason: str | None = Field(default=None, max_length=1600)

    @field_validator(
        "channel_roles",
        "channel_message_map",
        "channel_asset_map",
        "sequencing_dependencies",
        "channel_proof_requirements",
        "channel_risks",
        "early_execution_recommendations",
        "success_signals",
        "deferred_channels",
        "supporting_collateral_refs",
        mode="before",
    )
    @classmethod
    def _lists(cls, v: object) -> object:
        if v is None:
            return []
        return v


def validate_channel_execution_payload_dict(data: dict[str, object]) -> ChannelExecutionStructuredPayload:
    return ChannelExecutionStructuredPayload.model_validate(data)


class ChannelExecutionFrameworkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
