"""Provenance-aware composite adjustment (deterministic, payload-driven)."""

import pytest

from kaizen.signal import Signal
from kaizen.provenance_scoring import evaluate_provenance_layer
from kaizen.scoring_service import compute_signal_score


def _base_text() -> str:
    return (
        "Enterprise renewal risk: expected 95% retention; actual 82%; "
        "ARR exposure roughly $3m; validated in QBR with finance."
    )


def _envelope(
    source_type: str,
    *,
    author_type: str = "organization",
    channel: str = "icp-enterprise",
    refs: list | None = None,
    fingerprint: str | None = "fp1",
) -> dict:
    return {
        "source_type": source_type,
        "source_platform": "test_platform",
        "author_type": author_type,
        "channel_or_community": channel,
        "title": "Renewal analysis",
        "content_fingerprint": fingerprint,
        "evidence_refs": refs
        or [
            {"ref_type": "url", "ref_value": "https://example.com/qbr"},
            {"ref_type": "citation", "ref_value": "Internal QBR 2026-Q1"},
        ],
    }


def test_same_content_different_provenance_changes_composite():
    plain = {"text": _base_text(), "product": "billing"}
    deep = {
        "text": _base_text(),
        "product": "billing",
        "source_provenance": _envelope("deep_research_report"),
    }
    reddit = {
        "text": _base_text(),
        "product": "billing",
        "source_provenance": _envelope("reddit", author_type="individual", channel="r/saas"),
    }
    a = compute_signal_score(Signal(id=1, external_id="a", source="s", payload=plain))
    b = compute_signal_score(Signal(id=2, external_id="b", source="s", payload=deep))
    c = compute_signal_score(Signal(id=3, external_id="c", source="s", payload=reddit))
    assert "provenance:no_source_provenance_envelope" in a.rationale
    assert "provenance:mult=" in b.rationale
    assert b.composite_score > a.composite_score
    assert c.composite_score < b.composite_score
    assert b.source_authority_score is not None and b.source_authority_score > (c.source_authority_score or 0)


def test_deep_research_outranks_reddit_generic():
    body = _base_text()
    deep = compute_signal_score(
        Signal(
            id=1,
            external_id="d",
            source="s",
            payload={"text": body, "source_provenance": _envelope("deep_research_report")},
        ),
    )
    reddit = compute_signal_score(
        Signal(
            id=2,
            external_id="r",
            source="s",
            payload={
                "text": body,
                "source_provenance": _envelope(
                    "reddit",
                    author_type="individual",
                    channel="r/generic",
                    refs=[{"ref_type": "url", "ref_value": "https://reddit.com/x"}],
                ),
            },
        ),
    )
    assert deep.composite_score > reddit.composite_score


def test_promotional_language_increases_penalty_and_lowers_composite():
    clean = {
        "text": _base_text(),
        "source_provenance": _envelope("news_web", author_type="organization"),
    }
    spam = {
        "text": _base_text() + " Sponsored: buy now with promo code SAVE50. Affiliate link click here.",
        "source_provenance": _envelope("news_web", author_type="organization"),
    }
    a = compute_signal_score(Signal(id=1, external_id="a", source="s", payload=clean))
    b = compute_signal_score(Signal(id=2, external_id="b", source="s", payload=spam))
    assert (b.promotional_risk_penalty or 0) > (a.promotional_risk_penalty or 0)
    assert b.composite_score < a.composite_score


def test_deep_research_and_manual_note_evaluate_deterministically():
    sp_dr = _envelope("deep_research_report", fingerprint="aa")
    sp_mn = {
        "source_type": "manual_note",
        "source_platform": "manual_note",
        "author_type": "individual",
        "operator_id": "ops-1",
        "channel_or_community": "win-loss",
        "title": "Notes",
        "content_fingerprint": "mn-1",
        "evidence_refs": [{"ref_type": "url", "ref_value": "https://docs.example/1"}],
    }
    p1 = {"text": "note body", "source_provenance": sp_dr}
    p2 = {"text": "note body", "source_provenance": sp_mn}
    x = evaluate_provenance_layer(p1)
    y = evaluate_provenance_layer(p1)
    assert x == y
    assert x.applied
    mn = evaluate_provenance_layer(p2)
    assert mn.applied
    assert x.source_authority_score == pytest.approx(1.0)
    assert mn.source_authority_score == pytest.approx(0.90)