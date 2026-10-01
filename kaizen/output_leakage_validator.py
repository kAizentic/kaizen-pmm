"""Hard guards against research leakage in user-facing outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_BANNED_PHRASES = (
    "sources reviewed",
    "signals reviewed",
    "evidence table",
    "content_fingerprint",
    "derived from approved research buyer view",
    "deterministic default",
    "strategy generation is not run from this artifact",
    "plan alignment",
    "serialized evidence",
)

# Standalone token only (avoid false positives on words like "excerptable").
_BANNED_STANDALONE_WORDS: tuple[str, ...] = ("excerpt",)

_GENERIC_BANNED = (
    "optimize",
    "leverage",
    "scalable",
    "improve efficiency",
)

_SOURCE_ARRAY_RE = re.compile(r"\[\s*\{[^\]]*(?:source|source_type|source_platform)[^\]]*\}\s*\]", re.IGNORECASE)


@dataclass(frozen=True)
class LeakageViolation:
    code: str
    detail: str


class OutputValidationError(Exception):
    def __init__(self, violations: list[LeakageViolation]) -> None:
        self.violations = violations
        msg = "; ".join(f"{v.code}:{v.detail}" for v in violations)
        super().__init__(msg)


def _collect_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_collect_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_collect_text(v) for v in value)
    return str(value)


def validate_no_research_leakage(value: Any, *, allow_ellipsis: bool = False) -> None:
    text = _collect_text(value)
    low = text.lower()
    violations: list[LeakageViolation] = []
    for phrase in _BANNED_PHRASES:
        if phrase in low:
            violations.append(LeakageViolation("research_leakage_phrase", phrase))
    for word in _BANNED_STANDALONE_WORDS:
        if re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", low):
            violations.append(LeakageViolation("research_leakage_phrase", word))
    if _SOURCE_ARRAY_RE.search(text):
        violations.append(LeakageViolation("research_leakage_source_array", "raw serialized source array"))
    if not allow_ellipsis and "..." in text:
        violations.append(LeakageViolation("truncation_artifact", "..."))
    if violations:
        raise OutputValidationError(violations)


def validate_non_generic_strategy_language(value: Any) -> None:
    text = _collect_text(value).lower()
    violations: list[LeakageViolation] = []
    for phrase in _GENERIC_BANNED:
        if phrase in ("optimize", "leverage", "scalable"):
            if re.search(rf"\b{re.escape(phrase)}\b", text):
                violations.append(LeakageViolation("generic_strategy_language", phrase))
        elif phrase in text:
            violations.append(LeakageViolation("generic_strategy_language", phrase))
    if violations:
        raise OutputValidationError(violations)
