"""Gate behavior: each test writes a tiny run directory and asserts what the gate catches.

Every rule has a test that proves it fires, and the passing fixtures prove valid artifacts get through.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from kaizen.gate import run_gate


def _doc(source_type: str, platform: str, relation: str, body: str, published: str = "2026-08-01") -> str:
    return (
        f"---\nsource_type: {source_type}\nsource_platform: {platform}\nauthor_relation: {relation}\n"
        f"author_type: organization\npublished: {published}\n---\n{body}\n"
    )


CORPUS = {
    "a-brief.md": _doc(
        "deep_research_report",
        "analyst-brief",
        "independent",
        "Invoices spend a median of 9.4 days waiting for an approver. Exceptions take 61% of staff hours.\n"
        "Buyers who own the ERP module still struggle with approval routing for non-ERP users.\n"
        "We recommend that vendors sell approval control rather than capture speed.",
    ),
    "b-interview.md": _doc(
        "manual_note",
        "discovery-interview",
        "first_party",
        "The controller said approvals sat for weeks because plant managers batched them on Fridays.\n"
        "We won the deal because approvers acted from email without an ERP login.\n"
        "I would buy a tool that fixed this tomorrow.",
    ),
    "c-forum.md": _doc(
        "manual_note",
        "practitioner-forum",
        "independent",
        "Our module routes to one approver and stops, with no escalation and no delegation.\n"
        "We still chase approvals in a spreadsheet and over email every Monday.",
    ),
    "d-sponsored.md": _doc(
        "news_web",
        "vendor-blog",
        "sponsored",
        "Our customers see up to 90% faster processing with intelligent automation.",
    ),
}

# id, doc, quote, section, claim_type, evidence_kind, alternative, alternative_type
CLAIMS = [
    ("E01", "a-brief.md", "invoices spend a median of 9.4 days waiting for an approver", "key_problems", "fact", "market_data", None, None),
    ("E02", "a-brief.md", "Exceptions take 61% of staff hours", "key_problems", "fact", "market_data", None, None),
    ("E03", "b-interview.md", "approvals sat for weeks because plant managers batched them on Fridays", "key_problems", "fact", "past_episode", None, None),
    ("E04", "b-interview.md", "approvers acted from email without an ERP login", "competitive_landscape", "fact", "past_episode", None, None),
    ("E05", "c-forum.md", "routes to one approver and stops, with no escalation", "competitive_landscape", "fact", "observed_behavior", "ERP module", "vendor"),
    ("E06", "a-brief.md", "still struggle with approval routing for non-ERP users", "buyer_segments", "fact", "market_data", None, None),
    ("E07", "d-sponsored.md", "Our customers see up to 90% faster processing", "market_overview", "fact", "vendor_claim", None, None),
    ("E08", "c-forum.md", "We still chase approvals in a spreadsheet and over email", "competitive_landscape", "fact", "observed_behavior", "spreadsheets and email", "status_quo"),
    ("E09", "b-interview.md", "I would buy a tool that fixed this tomorrow", "buyer_segments", "persona_need", "prediction", None, None),
    ("E10", "a-brief.md", "We recommend that vendors sell approval control rather than capture speed", "market_overview", "recommendation", "market_data", None, None),
]


def _claim(row: tuple, **override) -> dict:
    i, d, q, s, ct, kind, alt, alt_t = row
    c = {
        "id": i,
        "claim": f"The source states that {q[:60]}.",
        "quote": q,
        "doc": d,
        "section": s,
        "claim_type": ct,
        "evidence_kind": kind,
    }
    if alt:
        c |= {"alternative": alt, "alternative_type": alt_t}
    return c | override


def _evidence(rows=CLAIMS, **override) -> dict:
    return {"corpus": "corpus", "claims": [_claim(r, **override) for r in rows]}


BRIEF = {
    "strategic_recommendation": "Win controllers who already own an ERP module by fixing approvals.",
    "recommended_icp": "Mid-market controllers with approvers outside finance",
    "excluded_icps": [
        {"item": "High-volume shops buying on cost per invoice", "reason": "They choose on price and never pilot.", "evidence": ["E02"]},
    ],
    "problem_frame": "Approvals, not data entry, hold invoices for days.",
    "wedge": "Approvals anyone can complete from email",
    "category_frame": "Approval layer on top of the ERP",
    "category_style": "subsegment",
    "differentiation_claim": "The ERP module routes to one approver and stops; we route and escalate across approvers outside finance.",
    "proof_requirements": ["Approval wait time before and after a pilot"],
    "preferred_gtm_motion": "Controller-led pilot on one business unit",
    "rejected_gtm_motions": [
        {"item": "Cost-per-invoice bake-offs", "reason": "Buyers who frame it on price stay with spreadsheets.", "evidence": ["E08"]},
    ],
    "assumptions": [
        {
            "assumption": "Controllers can get a read-only ERP connection approved quickly.",
            "what_would_falsify": "Pilots stall waiting on IT for more than a month.",
        },
    ],
    "decision_rationale": "Approval delay is the cost the ERP module leaves untouched in every source.",
}
BRIEF_CITES = {
    "strategic_recommendation": ["E01"],
    "recommended_icp": ["E06"],
    "problem_frame": ["E01", "E03"],
    "wedge": ["E04"],
    "differentiation_claim": ["E05", "E04"],
    "proof_requirements": ["E01"],
    "preferred_gtm_motion": ["E04"],
}


def _brief(payload: dict | None = None, citations: dict | None = None) -> dict:
    p = copy.deepcopy(BRIEF) | (payload or {})
    c = copy.deepcopy(BRIEF_CITES) | (citations or {})
    return {"stage": "strategy_brief", "payload": p, "citations": c}


SPINE = {
    "master_narrative": "Approvals, not data entry, hold invoices for days. Our approval layer on top of the ERP lets anyone approve from email.",
    "category_statement": "An approval layer on top of the ERP you already own.",
    "wedge_expression": "Approvals anyone can complete from email.",
    "value_pillars": ["Approvals that finish from email", "Escalation across approvers outside finance"],
    "persona_message_hierarchy": [
        {
            "persona": "Mid-market controllers with approvers outside finance",
            "headline": "Close the approval gap without replacing your ERP.",
            "supporting_proof": "A one-unit pilot measuring approval wait time.",
        },
    ],
    "proof_points": ["Approval wait time measured before and after a one-unit pilot"],
    "objection_map": ["We already own the ERP module: it routes to one approver and stops."],
    "forbidden_language": ["touchless"],
    "cta_logic": ["Start a one-unit pilot"],
    "downstream_asset_implications": ["Lead every asset with approval wait time", "Pilot offer in every CTA"],
}
SPINE_CITES = {
    "value_pillars.0": ["E04"],
    "value_pillars.1": ["E05"],
    "persona_message_hierarchy.0": ["E06"],
    "proof_points": ["E01"],
    "objection_map": ["E05"],
}


def _spine(payload: dict | None = None, citations: dict | None = None) -> dict:
    p = copy.deepcopy(SPINE) | (payload or {})
    c = copy.deepcopy(SPINE_CITES) | (citations or {})
    return {"stage": "message_spine", "payload": p, "citations": c}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "corpus").mkdir()
    for name, text in CORPUS.items():
        (tmp_path / "corpus" / name).write_text(text, encoding="utf-8")
    (tmp_path / "runs" / "r").mkdir(parents=True)
    return tmp_path


def _write(repo: Path, name: str, data: dict) -> None:
    (repo / "runs" / "r" / name).write_text(json.dumps(data), encoding="utf-8")


def _gate(repo: Path, stage: str):
    return run_gate(stage, repo / "runs" / "r", repo)


def _codes(report) -> list[str]:
    return [v.code for v in report.violations]


def _scored(repo: Path) -> dict:
    data = json.loads((repo / "runs/r/evidence.scored.json").read_text())
    return {c["id"]: c for c in data["claims"]}


# --- evidence -------------------------------------------------------------------------------


def test_evidence_passes(repo: Path) -> None:
    _write(repo, "evidence.json", _evidence())
    rpt = _gate(repo, "evidence")
    assert rpt.passed, rpt.violations
    assert rpt.metrics["vendor_claims"] == 1


def test_quote_not_in_source(repo: Path) -> None:
    rows = CLAIMS[:-1] + [("E10", "a-brief.md", "this sentence was never written by anyone", "key_problems", "fact", "market_data", None, None)]
    _write(repo, "evidence.json", _evidence(rows))
    rpt = _gate(repo, "evidence")
    assert "quote_not_in_source" in _codes(rpt)
    assert _scored(repo)["E10"]["admitted"] is False


def test_number_must_appear_in_quote(repo: Path) -> None:
    ev = _evidence()
    ev["claims"][0]["claim"] = "Invoices wait a median of 12 days for an approver."
    _write(repo, "evidence.json", ev)
    assert "number_not_in_quote" in _codes(_gate(repo, "evidence"))


def test_hypothetical_quote_cannot_be_behavior(repo: Path) -> None:
    ev = _evidence()
    ev["claims"][8]["evidence_kind"] = "past_episode"  # E09: "I would buy..."
    _write(repo, "evidence.json", ev)
    assert "hypothetical_tagged_as_behavior" in _codes(_gate(repo, "evidence"))


def test_vendor_source_must_be_vendor_claim(repo: Path) -> None:
    ev = _evidence()
    ev["claims"][6]["evidence_kind"] = "market_data"  # E07 from the sponsored post
    _write(repo, "evidence.json", ev)
    assert "vendor_source_not_vendor_claim" in _codes(_gate(repo, "evidence"))


def test_undeclared_promotional_source_is_treated_as_sponsored(repo: Path) -> None:
    (repo / "corpus" / "d-sponsored.md").write_text(
        _doc("news_web", "vendor-blog", "independent", "Sponsored. Our customers see up to 90% faster processing. Limited time: sign up now and use code X."),
        encoding="utf-8",
    )
    ev = _evidence()
    ev["claims"][6]["evidence_kind"] = "market_data"
    _write(repo, "evidence.json", ev)
    rpt = _gate(repo, "evidence")
    assert "vendor_source_not_vendor_claim" in _codes(rpt)
    assert "undeclared_promotional_source" in [w.code for w in rpt.warnings]


def test_agent_cannot_supply_scores(repo: Path) -> None:
    _write(repo, "evidence.json", _evidence(score_hints={"problem_clarity_score": 1.0}))
    assert "contract_violation" in _codes(_gate(repo, "evidence"))


def test_alternative_needs_its_type(repo: Path) -> None:
    ev = _evidence()
    del ev["claims"][4]["alternative_type"]
    _write(repo, "evidence.json", ev)
    assert "contract_violation" in _codes(_gate(repo, "evidence"))


def test_requires_enough_non_vendor_evidence(repo: Path) -> None:
    _write(repo, "evidence.json", _evidence(CLAIMS[:3] + [CLAIMS[6]]))
    assert "too_little_admitted_evidence" in _codes(_gate(repo, "evidence"))


def test_rewritten_document_shares_an_origin(repo: Path) -> None:
    body = CORPUS["a-brief.md"].split("---\n", 2)[2]
    (repo / "corpus" / "e-press.md").write_text(_doc("news_web", "trade-press", "independent", "As reported: " + body), encoding="utf-8")
    _write(repo, "evidence.json", _evidence())
    _gate(repo, "evidence")
    sources = json.loads((repo / "runs/r/evidence.scored.json").read_text())["sources"]
    assert sources["e-press.md"]["origin"] == sources["a-brief.md"]["origin"]
    assert sources["c-forum.md"]["origin"] != sources["b-interview.md"]["origin"]


def test_undated_source_warns(repo: Path) -> None:
    (repo / "corpus" / "c-forum.md").write_text(
        CORPUS["c-forum.md"].replace("published: 2026-08-01\n", ""), encoding="utf-8",
    )
    _write(repo, "evidence.json", _evidence())
    rpt = _gate(repo, "evidence")
    assert rpt.passed
    assert "undated_source" in [w.code for w in rpt.warnings]


# --- strategy brief -------------------------------------------------------------------------


@pytest.fixture
def evidenced(repo: Path) -> Path:
    _write(repo, "evidence.json", _evidence())
    assert _gate(repo, "evidence").passed
    return repo


def _brief_codes(repo: Path, **kw) -> list[str]:
    _write(repo, "strategy_brief.json", _brief(**kw))
    return _codes(_gate(repo, "strategy_brief"))


def test_strategy_brief_passes(evidenced: Path) -> None:
    _write(evidenced, "strategy_brief.json", _brief())
    rpt = _gate(evidenced, "strategy_brief")
    assert rpt.passed, rpt.violations


def test_blocked_until_evidence_passes(repo: Path) -> None:
    _write(repo, "strategy_brief.json", _brief())
    assert _codes(_gate(repo, "strategy_brief")) == ["upstream_not_passed"]


def test_single_origin_claim_fails(evidenced: Path) -> None:
    # E01 and E06 are both the analyst brief: one origin however many claims.
    assert "single_origin_claim" in _brief_codes(evidenced, citations={"differentiation_claim": ["E05", "E08"]})


def test_problem_frame_needs_two_methods(evidenced: Path) -> None:
    # E03 (interview) and E05 (forum) are two origins but one method (manual_note).
    assert "single_method_claim" in _brief_codes(evidenced, citations={"problem_frame": ["E03", "E05"]})


def test_predictions_do_not_carry_the_problem(evidenced: Path) -> None:
    codes = _brief_codes(evidenced, citations={"problem_frame": ["E09", "E07"]})
    assert "no_behavioral_or_market_evidence" in codes


def test_recommendation_only_support_fails(evidenced: Path) -> None:
    assert "rests_only_on_recommendations" in _brief_codes(evidenced, citations={"wedge": ["E10"]})


def test_differentiation_must_name_an_alternative(evidenced: Path) -> None:
    codes = _brief_codes(evidenced, payload={"differentiation_claim": "We route and escalate approvals across the whole company."})
    assert "differentiation_names_no_alternative" in codes


def test_status_quo_must_be_considered(evidenced: Path) -> None:
    rejected = [{"item": "Cost-per-invoice bake-offs", "reason": "We lose every deal framed on price.", "evidence": ["E02"]}]
    assert "status_quo_not_considered" in _brief_codes(evidenced, payload={"rejected_gtm_motions": rejected})


def test_exclusions_need_reason_and_evidence(evidenced: Path) -> None:
    no_reason = [{"item": "High-volume shops", "reason": "", "evidence": ["E02"]}]
    assert "contract_violation" in _brief_codes(evidenced, payload={"excluded_icps": no_reason})
    bad_ev = [{"item": "High-volume shops", "reason": "They choose on price and never pilot.", "evidence": ["E07"]}]
    assert "exclusion_evidence_invalid" not in _brief_codes(evidenced, payload={"excluded_icps": bad_ev})
    unknown = [{"item": "High-volume shops", "reason": "They choose on price and never pilot.", "evidence": ["E99"]}]
    assert "exclusion_evidence_invalid" in _brief_codes(evidenced, payload={"excluded_icps": unknown})


def test_assumptions_required(evidenced: Path) -> None:
    assert "contract_violation" in _brief_codes(evidenced, payload={"assumptions": []})


def test_hedged_commitment_fails(evidenced: Path) -> None:
    assert "hedged_commitment" in _brief_codes(evidenced, payload={"wedge": "We could explore email approvals"})


def test_icp_must_be_singular(evidenced: Path) -> None:
    codes = _brief_codes(evidenced, payload={"recommended_icp": "Mid-market controllers as well as enterprise AP teams"})
    assert "icp_not_singular" in codes


def test_generic_and_superlative_language_fail(evidenced: Path) -> None:
    codes = _brief_codes(evidenced, payload={"wedge": "Seamless approvals that leverage email"})
    assert "generic_strategy_language" in codes and "superlative_or_sameness" in codes


# --- message spine --------------------------------------------------------------------------


@pytest.fixture
def briefed(evidenced: Path) -> Path:
    _write(evidenced, "strategy_brief.json", _brief())
    assert _gate(evidenced, "strategy_brief").passed
    return evidenced


def _spine_codes(repo: Path, **kw) -> list[str]:
    _write(repo, "message_spine.json", _spine(**kw))
    return _codes(_gate(repo, "message_spine"))


def test_message_spine_passes(briefed: Path) -> None:
    _write(briefed, "message_spine.json", _spine())
    rpt = _gate(briefed, "message_spine")
    assert rpt.passed, rpt.violations


def test_too_many_pillars(briefed: Path) -> None:
    pillars = ["Approvals from email", "Escalation rules", "Exception trail", "Read-only setup", "Audit export"]
    cites = {f"value_pillars.{i}": ["E04"] for i in range(5)}
    assert "too_many_pillars" in _spine_codes(briefed, payload={"value_pillars": pillars}, citations=cites)


def test_pillar_without_proof(briefed: Path) -> None:
    cites = copy.deepcopy(SPINE_CITES)
    del cites["value_pillars.1"]
    _write(briefed, "message_spine.json", {"stage": "message_spine", "payload": SPINE, "citations": cites})
    assert "pillar_without_proof" in _codes(_gate(briefed, "message_spine"))


def test_duplicate_pillars(briefed: Path) -> None:
    pillars = ["Approvals that finish from email", "Approvals that finish from email fast"]
    assert "duplicate_pillars" in _spine_codes(briefed, payload={"value_pillars": pillars})


def test_persona_cannot_be_an_excluded_icp(briefed: Path) -> None:
    rows = [
        SPINE["persona_message_hierarchy"][0],
        {"persona": "High-volume shops buying on cost per invoice", "headline": "Lower cost per invoice.", "supporting_proof": "Pricing."},
    ]
    cites = {"persona_message_hierarchy.1": ["E02"]}
    assert "persona_is_excluded_icp" in _spine_codes(briefed, payload={"persona_message_hierarchy": rows}, citations=cites)


def test_support_wording_needs_strong_evidence(briefed: Path) -> None:
    payload = {"proof_points": ["Approval wait time cut 40% in a one-unit pilot"]}
    assert "unsubstantiated_claim" in _spine_codes(briefed, payload=payload, citations={"proof_points": ["E07"]})


def test_proof_requirement_must_map_to_a_proof_point(briefed: Path) -> None:
    assert "proof_requirement_unmapped" in _spine_codes(briefed, payload={"proof_points": ["Customer logos on the website"]})


def test_category_anchor(briefed: Path) -> None:
    codes = _spine_codes(briefed, payload={"category_statement": "Invoice automation for finance teams."})
    assert "category_anchor_missing" in codes


def test_wedge_anchor(briefed: Path) -> None:
    pillars = ["Faster month-end close", "Cleaner audit files"]
    assert "wedge_anchor_missing" in _spine_codes(briefed, payload={"value_pillars": pillars})


def test_spine_cannot_use_its_own_forbidden_language(briefed: Path) -> None:
    assert "uses_own_forbidden_language" in _spine_codes(briefed, payload={"forbidden_language": ["from email"]})
