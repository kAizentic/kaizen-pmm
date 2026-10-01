"""Cross-source corroboration layer (deterministic similarity + diversity + polarity guard)."""

from datetime import datetime, timezone

import pytest

from kaizen.signal import Signal
from kaizen.scoring_service import compute_signal_score

_TS = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

_SHARED = (
    "enterprise renewal risk arr exposure million dollars validated quarterly "
    "business review finance leadership pipeline forecast smb segment"
)


def _sp(st: str, plat: str) -> dict:
    return {
        "source_type": st,
        "source_platform": plat,
        "title": "Renewal theme",
    }


def _sig(i: int, ext: str, st: str, plat: str, text: str) -> Signal:
    return Signal(
        id=i,
        external_id=ext,
        source=plat,
        created_at=_TS,
        payload={"text": text, "source_provenance": _sp(st, plat)},
    )


def test_single_signal_no_peers_no_corroboration_boost():
    s = _sig(1, "a", "reddit", "reddit", _SHARED)
    out = compute_signal_score(s, peer_signals=None)
    assert out.corroboration_peer_count == 0
    assert out.corroboration_composite_multiplier == pytest.approx(1.0)
    assert out.corroboration_score == pytest.approx(0.0)
    assert "no_peer_context" in (out.corroboration_adjustment_reason or "")


def test_similar_sources_same_identity_no_boost():
    """Same source_type and platform → only one identity → diversity fails."""
    a = _sig(1, "a", "reddit", "reddit", _SHARED)
    b = _sig(2, "b", "reddit", "reddit", _SHARED)
    out = compute_signal_score(a, peer_signals=[b])
    assert out.corroboration_peer_count >= 1
    assert out.corroboration_score == pytest.approx(0.0)
    assert "insufficient_cross_source_diversity" in (out.corroboration_adjustment_reason or "")


def test_diverse_platforms_corroboration_boosts():
    a = _sig(1, "a", "reddit", "reddit", _SHARED)
    b = _sig(2, "b", "news_web", "cnn", _SHARED)
    solo = compute_signal_score(a, peer_signals=[])
    with_peer = compute_signal_score(a, peer_signals=[b])
    assert solo.corroboration_score == pytest.approx(0.0)
    assert with_peer.corroboration_peer_count == 1
    assert with_peer.corroboration_score > 0
    assert with_peer.corroboration_composite_multiplier > solo.corroboration_composite_multiplier
    assert with_peer.composite_score > solo.composite_score


def test_multiple_weak_diverse_sources_boost_more_than_one_peer():
    base = _SHARED
    target = _sig(1, "t", "reddit", "reddit", base)
    p2 = _sig(2, "n", "news_web", "cnn", base)
    p3 = _sig(3, "y", "youtube", "yt", base)
    one = compute_signal_score(target, peer_signals=[p2])
    two = compute_signal_score(target, peer_signals=[p2, p3])
    assert two.corroboration_peer_count >= one.corroboration_peer_count
    assert two.corroboration_score >= one.corroboration_score
    assert two.composite_score >= one.composite_score


def test_polarity_conflict_excludes_peer_no_boost():
    a = _sig(1, "a", "reddit", "r1", _SHARED + " growth expansion wins improved revenue")
    b = _sig(2, "b", "news_web", "cnn", _SHARED + " decline loss dropped churn worsened")
    out = compute_signal_score(a, peer_signals=[b])
    assert out.corroboration_peer_count == 0
    assert out.corroboration_score == pytest.approx(0.0)


def test_isolated_low_similarity_no_boost():
    a = _sig(1, "a", "reddit", "r1", _SHARED)
    b = _sig(2, "b", "news_web", "cnn", "completely unrelated text about cats and weather tables")
    out = compute_signal_score(a, peer_signals=[b])
    assert out.corroboration_peer_count == 0
    assert "no_similar_peers" in (out.corroboration_adjustment_reason or "")
