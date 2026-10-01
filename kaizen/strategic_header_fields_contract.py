"""
Typed contract for normalized strategic header fields (research + strategy brief headers).

These four strings are the highest-trust layer: only explicit commitments, eligible
high-confidence assertions, or structured gaps — never silent weak backfill.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


STRUCTURED_GAP_PREFIX = "**Structured gap"


def is_structured_gap_placeholder(text: str) -> bool:
    """True when the field intentionally signals operator review (no weak prose)."""
    t = (text or "").strip()
    return t.startswith(STRUCTURED_GAP_PREFIX) or "[operator review]" in t.lower()


class HeaderQualityStatus(StrEnum):
    all_passed = "all_passed"
    partial = "partial"
    blocked = "blocked"


class PerFieldHeaderProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    selected_source_ids: list[str] = Field(default_factory=list)
    selected_assertion_ids: list[str] = Field(default_factory=list)
    quality_notes: str = Field(default="", max_length=800)
    # Ranking pass: best-valid selection (optional for backward-compatible evidence rows)
    selected_candidate_text: str | None = Field(default=None, max_length=1200)
    selected_candidate_score: float | None = None
    why_selected: str | None = Field(default=None, max_length=800)
    rejected_candidates_count: int | None = Field(default=None, ge=0)
    top_rejected_candidate_text: str | None = Field(default=None, max_length=1200)
    top_rejected_candidate_reason: str | None = Field(default=None, max_length=400)


class StrategicHeaderFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    strategic_wedge: str = Field(..., min_length=4, max_length=1200)
    positioning: str = Field(..., min_length=4, max_length=1200)
    why_competitors_lose: str = Field(..., min_length=4, max_length=1200)
    buying_trigger: str = Field(..., min_length=4, max_length=1200)
    header_quality_status: HeaderQualityStatus
    blocked_fields: list[str] = Field(default_factory=list)
    rejection_reasons: dict[str, list[str]] = Field(default_factory=dict)
    provenance: dict[str, PerFieldHeaderProvenance] = Field(default_factory=dict)
    upstream_header_candidate_debug: dict[str, Any] | None = Field(
        default=None,
        description="Pre-selection synthesis/completion previews for evidence_table debugging.",
    )


def structured_gap_markdown(field_label: str, detail: str = "") -> str:
    """Operator-visible gap line; must stay above ResearchDecisionRecord min lengths."""
    suffix = f" {detail}" if detail else ""
    return (
        f"{STRUCTURED_GAP_PREFIX} — operator review:** No clean **{field_label}** passed header normalization gates.{suffix} "
        "See `evidence_table` row `kind=strategic_header_fields` for `rejection_reasons`."
    )
