"""A scored unit of evidence: one claim extracted from the research corpus.

Plain data, no persistence. The evidence stage writes these as JSON; scoring and
corroboration read them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Signal:
    id: int
    payload: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    external_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
