"""Deterministic PMM decision-quality scoring with coherence chain (no external APIs)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from kaizen.corroboration_scoring import evaluate_corroboration
from kaizen.signal import Signal
from kaizen.provenance_scoring import evaluate_provenance_layer
from kaizen.scoring_threshold import assign_priority_tier, build_promotion_blockers

_SCORE_KEYS = (
    "problem_clarity_score",
    "buyer_salience_score",
    "commercial_impact_score",
    "differentiation_opening_score",
    "evidence_strength_score",
    "actionability_now_score",
)

_CHAIN_KEYS = (
    "problem_clarity_score",
    "buyer_salience_score",
    "commercial_impact_score",
    "evidence_strength_score",
)

_HINT_KEYS = frozenset(_SCORE_KEYS)

_WEIGHTS: dict[str, float] = {
    "problem_clarity_score": 0.24,
    "buyer_salience_score": 0.16,
    "commercial_impact_score": 0.22,
    "differentiation_opening_score": 0.18,
    "evidence_strength_score": 0.12,
    "actionability_now_score": 0.08,
}

_CHAIN_THRESHOLD = 0.22
_COMM_ANCHOR_THRESHOLD = 0.18
_COHERENCE_TIER_CAP = 0.75
_COMPOSITE_COHERENCE_BLEND = (0.65, 0.35)

_PROBLEM_KWS = (
    "reproduce",
    "expected",
    "actual",
    "steps",
    "workaround",
    "symptom",
    "root cause",
    "instead of",
    "error",
    "fails",
    "cannot",
    "unable",
    "what happens",
    "when user",
    "behavior",
)

_PROBLEM_PAYLOAD_KEYS = frozenset(
    {
        "problem",
        "issue",
        "symptom",
        "error",
        "bug",
        "steps_to_reproduce",
        "expected_behavior",
        "actual_behavior",
    },
)

_BUYER_KWS = (
    "segment",
    "persona",
    "icp",
    "buyer",
    "customer",
    "champion",
    "economic buyer",
    "cfo",
    "vp sales",
    "sales leader",
    "smb",
    "enterprise",
    "mid-market",
    "end user",
    "procurement",
)

_BUYER_PAYLOAD_KEYS = frozenset({"segment", "persona", "buyer", "icp", "role", "title", "company_size"})

_COMMERCIAL_KWS = (
    "revenue",
    "churn",
    "arr",
    "mrr",
    "pipeline",
    "quota",
    "renewal",
    "downgrade",
    "expansion",
    "contract",
    "budget",
    "roi",
    "cost",
    "savings",
    "win rate",
    "deal size",
    "retention",
)

_COMMERCIAL_PAYLOAD_KEYS = frozenset(
    {"arr", "mrr", "revenue", "churn", "pipeline_impact", "impact", "acv"},
)

_DIFF_KWS = (
    "competitor",
    "versus",
    " vs ",
    "alternative",
    "incumbent",
    "switch",
    "migrate",
    "bake-off",
    "tradeoff",
    "trade-off",
    "evaluate",
    "moat",
    "differentiation",
    "replace",
    "compared to",
)

_DIFF_PAYLOAD_KEYS = frozenset({"competitors", "vs", "differentiation", "alternatives"})

_CONCRETE_CORPUS = (
    "workflow",
    "product",
    "feature",
    "integration",
    "dashboard",
    "platform",
    "module",
    "api",
)

_CONCRETE_PAYLOAD_KEYS = frozenset(
    {"product", "workflow", "feature", "integration", "product_area", "module"},
)

_ACTION_KWS = (
    "deadline",
    "need by",
    "this quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "fy20",
    "board",
    "approval",
    "pilot",
    "timeline",
    "next week",
    "escalate",
    "waiting on",
    "decision needed",
    "legal review",
    "security review",
    "budget freeze",
    "go-live",
)

_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_QUOTE_SPAN_RE = re.compile(r'"[^"]{12,}"')
_URL_RE = re.compile(r"https?://[^\s\"']+", re.IGNORECASE)
_UNIT_NUMBER_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(%|\$|usd|eur|gbp|arr|mrr|users|customers|days|weeks|months|seats|nps|bps)\b",
    re.IGNORECASE,
)


def _clamp_unit(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _payload_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def _payload_without_hints(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "score_hints"}


def _hint_for_key(payload: dict[str, Any], key: str) -> float | None:
    hints = payload.get("score_hints")
    if isinstance(hints, dict):
        v = hints.get(key)
        if isinstance(v, bool):
            return float(v)
        if isinstance(v, (int, float)):
            return float(v)
    v = payload.get(key)
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _count_hints(payload: dict[str, Any]) -> int:
    return sum(1 for k in _SCORE_KEYS if _hint_for_key(payload, k) is not None)


def _payload_text_for_corpus(payload: Any) -> str:
    if isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True)
    if isinstance(payload, list):
        return json.dumps(payload, sort_keys=True)
    if payload is None:
        return ""
    return str(payload)


def _corpus_for_payload(signal: Signal, payload_dict: dict[str, Any]) -> str:
    parts: list[str] = []
    if signal.source:
        parts.append(signal.source)
    if signal.external_id:
        parts.append(signal.external_id)
    parts.append(_payload_text_for_corpus(payload_dict))
    return " ".join(parts).lower()


def _corpus(signal: Signal) -> str:
    return _corpus_for_payload(signal, _payload_dict(signal.payload))


def _keyword_hits(corpus: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in corpus)


def _payload_key_hits(payload: dict[str, Any], keys: frozenset[str]) -> int:
    pl = {str(k).lower() for k in payload}
    return sum(1 for k in keys if k in pl)


def _walk_payload_values(obj: Any) -> Iterator[Any]:
    if isinstance(obj, dict):
        for x in obj.values():
            yield from _walk_payload_values(x)
    elif isinstance(obj, list):
        for x in obj:
            yield from _walk_payload_values(x)
    else:
        yield obj


def _long_string_count(payload: Any) -> int:
    n = 0
    for v in _walk_payload_values(payload):
        if isinstance(v, str) and len(v) >= 80:
            n += 1
    return n


def _unit_number_score(blob: str) -> float:
    hits = len(_UNIT_NUMBER_RE.findall(blob))
    return min(1.0, hits * 0.14)


def _url_weight_sum(corpus: str) -> float:
    urls = _URL_RE.findall(corpus)
    total = 0.0
    for u in urls:
        low = u.lower()
        if any(x in low for x in ("github.com", ".gov", "wikipedia.org", "arxiv.org", "nih.gov")):
            total += 0.22
        elif any(x in low for x in ("bit.ly", "t.co", "goo.gl", "tinyurl", "ow.ly")):
            total += 0.06
        else:
            total += 0.12
    return min(1.0, total)


def _has_concrete_context(corpus: str, payload: dict[str, Any]) -> bool:
    if any(c in corpus for c in _CONCRETE_CORPUS):
        return True
    keys = {str(k).lower() for k in payload}
    return bool(keys & _CONCRETE_PAYLOAD_KEYS)


def _heuristic_problem_clarity(corpus: str, payload: dict[str, Any]) -> tuple[float, str]:
    hits = _keyword_hits(corpus, _PROBLEM_KWS)
    qmarks = min(corpus.count("?"), 5)
    pk = _payload_key_hits(payload, _PROBLEM_PAYLOAD_KEYS)
    raw = min(1.0, hits * 0.12 + qmarks * 0.06 + pk * 0.1)
    v = _clamp_unit(raw)
    return v, f"heuristic:problem_kw={hits};questions={qmarks};payload_keys={pk}"


def _heuristic_buyer_salience(corpus: str, payload: dict[str, Any]) -> tuple[float, str]:
    hits = _keyword_hits(corpus, _BUYER_KWS)
    bk = _payload_key_hits(payload, _BUYER_PAYLOAD_KEYS)
    raw = min(1.0, hits * 0.14 + bk * 0.12)
    v = _clamp_unit(raw)
    return v, f"heuristic:buyer_kw={hits};payload_keys={bk}"


def _heuristic_commercial_impact(corpus: str, payload: dict[str, Any]) -> tuple[float, str]:
    hits = _keyword_hits(corpus, _COMMERCIAL_KWS)
    ck = _payload_key_hits(payload, _COMMERCIAL_PAYLOAD_KEYS)
    sym = (1 if "$" in corpus else 0) + (1 if "%" in corpus else 0)
    raw = min(1.0, hits * 0.13 + ck * 0.12 + sym * 0.08)
    v = _clamp_unit(raw)
    return v, f"heuristic:commercial_kw={hits};payload_keys={ck};symbols={sym}"


def _heuristic_differentiation_opening(corpus: str, payload: dict[str, Any]) -> tuple[float, str]:
    hits = _keyword_hits(corpus, _DIFF_KWS)
    dk = _payload_key_hits(payload, _DIFF_PAYLOAD_KEYS)
    raw = min(1.0, hits * 0.15 + dk * 0.14)
    v = _clamp_unit(raw)
    return v, f"heuristic:diff_kw={hits};payload_keys={dk}"


def _heuristic_evidence_strength(payload: Any, corpus: str) -> tuple[float, str]:
    blob = corpus + _payload_text_for_corpus(payload)
    unit_score = _unit_number_score(blob)
    url_score = _url_weight_sum(corpus)
    quotes = len(_QUOTE_SPAN_RE.findall(corpus))
    long_n = _long_string_count(payload)
    long_corpus = min(0.18, max(0.0, (len(corpus) - 180) / 1400.0))
    raw = (
        unit_score
        + url_score * 0.85
        + min(0.16, quotes * 0.05)
        + min(0.1, long_n * 0.035)
        + long_corpus
    )
    v = _clamp_unit(min(1.0, raw))
    return (
        v,
        f"heuristic:unit_metric={unit_score:.3f};urls_w={url_score:.3f};quotes={quotes};"
        f"long_text={long_n};corpus_tail={long_corpus:.3f}",
    )


def _heuristic_actionability_now(corpus: str) -> tuple[float, str]:
    hits = _keyword_hits(corpus, _ACTION_KWS)
    dates = 1 if _ISO_DATE_RE.search(corpus) else 0
    raw = min(1.0, hits * 0.14 + dates * 0.2)
    v = _clamp_unit(raw)
    return v, f"heuristic:action_kw={hits};iso_dates={dates}"


def _heuristic_for_key(
    key: str,
    signal: Signal,
    payload: dict[str, Any],
    corpus: str,
) -> tuple[float, str]:
    if key == "problem_clarity_score":
        return _heuristic_problem_clarity(corpus, payload)
    if key == "buyer_salience_score":
        return _heuristic_buyer_salience(corpus, payload)
    if key == "commercial_impact_score":
        return _heuristic_commercial_impact(corpus, payload)
    if key == "differentiation_opening_score":
        return _heuristic_differentiation_opening(corpus, payload)
    if key == "evidence_strength_score":
        return _heuristic_evidence_strength(signal.payload, corpus)
    if key == "actionability_now_score":
        return _heuristic_actionability_now(corpus)
    raise ValueError(key)


def _weighted_composite(values: dict[str, float]) -> float:
    return sum(_WEIGHTS[k] * values[k] for k in _SCORE_KEYS)


def _coherence_from_values(
    problem: float,
    buyer: float,
    commercial: float,
    evidence: float,
) -> float:
    flags = (
        problem >= _CHAIN_THRESHOLD,
        buyer >= _CHAIN_THRESHOLD,
        commercial >= _CHAIN_THRESHOLD,
        evidence >= _CHAIN_THRESHOLD,
    )
    return sum(1 for f in flags if f) / 4.0


def _apply_commercial_anchor(problem: float, buyer: float, commercial: float) -> float:
    if problem < _COMM_ANCHOR_THRESHOLD and buyer < _COMM_ANCHOR_THRESHOLD:
        return _clamp_unit(commercial * 0.42)
    return commercial


def _apply_diff_concrete(corpus: str, payload: dict[str, Any], diff: float) -> float:
    if not _has_concrete_context(corpus, payload):
        return _clamp_unit(diff * 0.5)
    return diff


@dataclass(frozen=True)
class ComputedSignalScore:
    problem_clarity_score: float
    buyer_salience_score: float
    commercial_impact_score: float
    differentiation_opening_score: float
    evidence_strength_score: float
    actionability_now_score: float
    coherence_score: float
    composite_score: float
    priority_tier: str
    rationale: str
    failed_problem_clarity: bool
    failed_evidence: bool
    failed_coherence: bool
    commercial_anchor_triggered: bool
    differentiation_penalty_applied: bool
    promotion_blockers: tuple[str, ...]
    source_authority_score: float | None
    source_signal_quality_score: float | None
    promotional_risk_penalty: float | None
    provenance_composite_multiplier: float | None
    provenance_adjustment_reason: str | None
    corroboration_score: float
    corroboration_composite_multiplier: float
    corroboration_peer_count: int
    corroboration_distinct_sources: int
    corroboration_adjustment_reason: str | None


def compute_signal_score(
    signal: Signal,
    peer_signals: Sequence[Signal] | None = None,
) -> ComputedSignalScore:
    """
    Six dimensions, hint integrity, co-occurrence discounts, coherence chain,
    composite adjustment, tier gates.
    """
    payload = _payload_dict(signal.payload)
    corpus = _corpus(signal)
    hint_count = _count_hints(payload)

    heur: dict[str, tuple[float, str]] = {}
    for key in _SCORE_KEYS:
        heur[key] = _heuristic_for_key(key, signal, payload, corpus)

    values: dict[str, float] = {}
    rationale_parts: list[str] = []

    for key in _SCORE_KEYS:
        hv, why = heur[key]
        hinted = _hint_for_key(payload, key)
        if hinted is None:
            values[key] = hv
            rationale_parts.append(f"{key}={hv:.4f}({why})")
        else:
            hint = _clamp_unit(hinted)
            if hint_count == 1:
                merged = _clamp_unit((hint + hv) / 2.0)
                tag = "(hint_integrity_avg1)"
            elif 2 <= hint_count <= 3:
                merged = _clamp_unit(0.65 * hint + 0.35 * hv)
                tag = f"(hint_integrity_blend{hint_count})"
            else:
                merged = hint
                tag = "(hint)"
            values[key] = merged
            rationale_parts.append(f"{key}={merged:.4f}{tag};heur_base={hv:.4f}")

    comm_raw = values["commercial_impact_score"]
    values["commercial_impact_score"] = _apply_commercial_anchor(
        values["problem_clarity_score"],
        values["buyer_salience_score"],
        comm_raw,
    )
    if values["commercial_impact_score"] != comm_raw:
        rationale_parts.append(
            f"cooc:commercial_anchor(discount={values['commercial_impact_score'] / max(comm_raw, 1e-6):.2f})",
        )

    diff_raw = values["differentiation_opening_score"]
    values["differentiation_opening_score"] = _apply_diff_concrete(corpus, payload, diff_raw)
    if values["differentiation_opening_score"] != diff_raw:
        rationale_parts.append("cooc:diff_requires_concrete_context")

    for k in _SCORE_KEYS:
        values[k] = _clamp_unit(values[k])

    coherence_observed = _coherence_from_values(
        values["problem_clarity_score"],
        values["buyer_salience_score"],
        values["commercial_impact_score"],
        values["evidence_strength_score"],
    )

    payload_clean = _payload_without_hints(payload)
    corp_h = _corpus_for_payload(signal, payload_clean)
    hp, _ = _heuristic_problem_clarity(corp_h, payload_clean)
    hb, _ = _heuristic_buyer_salience(corp_h, payload_clean)
    hcom_raw, _ = _heuristic_commercial_impact(corp_h, payload_clean)
    hcom = _apply_commercial_anchor(hp, hb, hcom_raw)
    hev, _ = _heuristic_evidence_strength(signal.payload, corp_h)
    hev = _clamp_unit(hev)
    coherence_heur = _coherence_from_values(hp, hb, hcom, hev)

    if hint_count == 0 or hint_count >= 4:
        coherence_score = coherence_observed
    else:
        coherence_score = min(coherence_observed, coherence_heur)

    rationale_parts.append(
        f"coherence_score={coherence_score:.4f}(obs={coherence_observed:.4f};heur_chain={coherence_heur:.4f};hints={hint_count})",
    )

    composite_weighted = _weighted_composite(values)
    a, b = _COMPOSITE_COHERENCE_BLEND
    composite_adjusted = _clamp_unit(composite_weighted * (a + b * coherence_score))
    rationale_parts.append(
        f"composite_weighted={composite_weighted:.4f};composite_adjusted={composite_adjusted:.4f}",
    )

    prov = evaluate_provenance_layer(payload)
    if prov.applied:
        composite_post_prov = _clamp_unit(composite_adjusted * prov.provenance_composite_multiplier)
        rationale_parts.append(prov.provenance_adjustment_reason or "provenance:applied")
        rationale_parts.append(
            f"composite_after_provenance={composite_post_prov:.4f}(pre={composite_adjusted:.4f})",
        )
        prov_auth = prov.source_authority_score
        prov_qual = prov.source_signal_quality_score
        prov_pen = prov.promotional_risk_penalty
        prov_mult = prov.provenance_composite_multiplier
        prov_reason = prov.provenance_adjustment_reason
    else:
        composite_post_prov = composite_adjusted
        rationale_parts.append("provenance:no_source_provenance_envelope;composite_unchanged")
        prov_auth = None
        prov_qual = None
        prov_pen = None
        prov_mult = None
        prov_reason = None

    corp = evaluate_corroboration(signal, list(peer_signals) if peer_signals is not None else None)
    composite_final = _clamp_unit(composite_post_prov * corp.corroboration_composite_multiplier)
    rationale_parts.append(corp.corroboration_adjustment_reason)
    rationale_parts.append(
        f"composite_after_corroboration={composite_final:.4f}(pre={composite_post_prov:.4f})",
    )

    tier = assign_priority_tier(
        composite_final,
        problem_clarity_score=values["problem_clarity_score"],
        buyer_salience_score=values["buyer_salience_score"],
        commercial_impact_score=values["commercial_impact_score"],
        differentiation_opening_score=values["differentiation_opening_score"],
        evidence_strength_score=values["evidence_strength_score"],
        actionability_now_score=values["actionability_now_score"],
        coherence_score=coherence_score,
    )

    rationale = "; ".join(rationale_parts)

    prob = values["problem_clarity_score"]
    ev = values["evidence_strength_score"]
    failed_problem_clarity = prob < 0.25
    failed_evidence = ev < 0.15
    failed_coherence = coherence_score < 0.75
    commercial_anchor_triggered = prob < _COMM_ANCHOR_THRESHOLD and values["buyer_salience_score"] < _COMM_ANCHOR_THRESHOLD
    differentiation_penalty_applied = (not _has_concrete_context(corpus, payload)) and diff_raw > 0.0

    blockers = build_promotion_blockers(
        tier,
        composite_score=composite_final,
        coherence_score=coherence_score,
        problem_clarity_score=prob,
        evidence_strength_score=ev,
    )

    return ComputedSignalScore(
        problem_clarity_score=values["problem_clarity_score"],
        buyer_salience_score=values["buyer_salience_score"],
        commercial_impact_score=values["commercial_impact_score"],
        differentiation_opening_score=values["differentiation_opening_score"],
        evidence_strength_score=values["evidence_strength_score"],
        actionability_now_score=values["actionability_now_score"],
        coherence_score=coherence_score,
        composite_score=composite_final,
        priority_tier=tier,
        rationale=rationale,
        failed_problem_clarity=failed_problem_clarity,
        failed_evidence=failed_evidence,
        failed_coherence=failed_coherence,
        commercial_anchor_triggered=commercial_anchor_triggered,
        differentiation_penalty_applied=differentiation_penalty_applied,
        promotion_blockers=tuple(blockers),
        source_authority_score=prov_auth,
        source_signal_quality_score=prov_qual,
        promotional_risk_penalty=prov_pen,
        provenance_composite_multiplier=prov_mult,
        provenance_adjustment_reason=prov_reason,
        corroboration_score=corp.corroboration_score,
        corroboration_composite_multiplier=corp.corroboration_composite_multiplier,
        corroboration_peer_count=corp.corroboration_peer_count,
        corroboration_distinct_sources=corp.corroboration_distinct_sources,
        corroboration_adjustment_reason=corp.corroboration_adjustment_reason,
    )
