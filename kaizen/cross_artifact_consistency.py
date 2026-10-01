"""
Cross-artifact narrative consistency across one-pager, channel execution, and messaging brief shapes.

Canonical-field-first precedence (evaluation only — does not change artifact text):
1) Prefer narrow typed slots that carry positioning / wedge / proof identity (category_line,
   product_definition, messaging category_frame / positioning, proof highlights, targeted CEP fields).
2) Broad artifact blobs (`_blob_one_pager`, `_blob_messaging`, `_blob_cep`) are fallback when
   canonical surfaces are absent or empty.
3) Metric reference tokens prefer strategy decision proof_requirements plus PMM proof_points and
   non-TAM-skewed key_metrics; evidence-table TAM blocks are de-weighted unless no other reference exists.
"""

from __future__ import annotations

import json
import re

from kaizen.approved_pmm_strategy_contract import (
    ApprovedPMMStrategy,
    ApprovedPMMStrategyCoherenceReport,
    MessagingBriefAssetShapeContract,
)
from kaizen.approved_pmm_strategy_gates import validate_channel_execution_payload_rows_against_pmm
from kaizen.channel_execution_contract import ChannelExecutionFrameworkError, ChannelExecutionStructuredPayload
from kaizen.collateral_contract import CollateralFrameworkError, OnePagerStructuredPayload
from kaizen.cross_artifact_consistency_contract import (
    AlignmentSeverity,
    ArtifactAlignmentNote,
    CrossArtifactConsistencyReport,
)
from kaizen.strategy_brief_contract import StrategyBriefStructuredPayload


def _tok(s: str) -> set[str]:
    return {m.group(0) for m in re.finditer(r"[a-z0-9]{3,}", (s or "").lower())}


def _jac(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _blob_one_pager(p: OnePagerStructuredPayload) -> str:
    return " ".join(
        [
            p.headline,
            p.category_line,
            p.problem_statement,
            p.urgency_statement,
            p.product_definition,
            " ".join(p.differentiators),
            " ".join(p.proof_highlights),
            p.target_buyer_summary,
            p.buying_trigger,
            p.target_persona,
            p.cta,
        ],
    )


def _blob_messaging(m: MessagingBriefAssetShapeContract) -> str:
    return " ".join(
        [m.category_frame, m.positioning, m.icp, " ".join(m.pains), " ".join(m.proof_points), " ".join(m.differentiation), m.talk_track],
    )


def _blob_cep(c: ChannelExecutionStructuredPayload) -> str:
    """Include plan-level CEP copy so cross-checks see the same commercial spine as human readers."""
    parts: list[str] = []
    for ch in c.prioritized_channels[:8]:
        parts.extend([ch.objective, ch.message_emphasis, ch.proof_needed, ch.success_signal])
    parts.extend(c.channel_message_map)
    parts.extend(c.channel_roles)
    parts.extend(c.early_execution_recommendations[:4])
    return " ".join(parts)


def _economic_density(text: str) -> float:
    low = text.lower()
    return min(1.0, sum(0.12 for k in ("roi", "budget", "cfo", "finance", "renewal", "tco", "capex") if k in low))


def _technical_density(text: str) -> float:
    low = text.lower()
    return min(1.0, sum(0.1 for k in ("kernel", "tensor", "latency", "serialization", "opcode", "microbench") if k in low))


def _plg_density(text: str) -> float:
    low = text.lower()
    return min(1.0, sum(0.2 for k in ("plg", "freemium", "self-serve", "viral", "credit card") if k in low))


def _enterprise_density(text: str) -> float:
    low = text.lower()
    return min(1.0, sum(0.12 for k in ("enterprise", "procurement", "committee", "on-prem", "hybrid") if k in low))


def _present(**kwargs: object) -> set[str]:
    out: set[str] = set()
    if kwargs.get("one_pager") is not None:
        out.add("one_pager")
    if kwargs.get("messaging_brief") is not None:
        out.add("messaging_brief")
    if kwargs.get("channel_execution") is not None:
        out.add("channel_execution")
    return out


_MIN_CANON_POSITION = 8
_MIN_WEDGE_SURFACE = 20
_MIN_GTM_SURFACE = 24


def _looks_tam_only_metric_line(s: str) -> bool:
    """Heuristic: long market-sizing lines that should not dominate metric reference tokens."""
    low = (s or "").lower()
    if len(s or "") < 28:
        return False
    hits = sum(1 for k in ("tam", "total addressable", "$900", "$125", "idc", "billion addressable market", "north america ai infrastructure") if k in low)
    return hits >= 2


def _metric_reference_tokens(
    pmm: ApprovedPMMStrategy,
    strategy_decision: StrategyBriefStructuredPayload | None,
) -> set[str]:
    parts: list[str] = []
    if strategy_decision is not None:
        parts.extend(strategy_decision.proof_requirements or [])
    parts.extend(pmm.proof_points or [])
    for m in pmm.key_metrics or []:
        if m and not _looks_tam_only_metric_line(m):
            parts.append(m)
    if not parts and pmm.key_metrics:
        parts.extend(m for m in pmm.key_metrics if m)
    return _tok(" ".join(parts))


def _one_pager_positioning_surface(op: OnePagerStructuredPayload) -> tuple[str, bool]:
    cat = (op.category_line or "").strip()
    pd = (op.product_definition or "").strip()
    if len(cat) >= _MIN_CANON_POSITION or len(pd) >= _MIN_CANON_POSITION:
        return " ".join([cat, pd]).strip(), True
    return _blob_one_pager(op), False


def _messaging_positioning_surface(mb: MessagingBriefAssetShapeContract) -> tuple[str, bool]:
    cf = (mb.category_frame or "").strip()
    pos = (mb.positioning or "").strip()
    if len(cf) >= _MIN_CANON_POSITION or len(pos) >= _MIN_CANON_POSITION:
        return " ".join([cf, pos]).strip(), True
    return _blob_messaging(mb), False


def _positioning_score_to_pp(*, surface: str, category: str, positioning: str, pp: set[str], use_full_blob_fallback: str) -> float:
    """Jaccard vs positioning_frame tokens; max over category, positioning, combined; optional full-blob fallback."""
    scores: list[float] = []
    for slot in (category, positioning, surface):
        if (slot or "").strip():
            scores.append(_jac(_tok(slot), pp))
    if not scores and use_full_blob_fallback.strip():
        scores.append(_jac(_tok(use_full_blob_fallback), pp))
    return max(scores) if scores else 0.0


def _wedge_score_surface(blob: str, pw: set[str], pp: set[str]) -> float:
    """Same blend as legacy wscore: wedge + positioning vs same blob tokens."""
    if not (blob or "").strip():
        return 0.75
    t = _tok(blob)
    inner = max(_jac(t, pw), _jac(t, pp) * 0.85)
    return max(0.0, min(1.0, 0.45 + 0.55 * inner))


def _one_pager_wedge_surface(op: OnePagerStructuredPayload) -> tuple[str, bool]:
    headline = (op.headline or "").strip()
    sub = (op.subhead or "").strip()
    prob = (op.problem_statement or "").strip()
    lead = prob[:480] if prob else ""
    combined = " ".join([headline, sub, lead]).strip()
    if len(combined) >= _MIN_WEDGE_SURFACE:
        return combined, True
    return _blob_one_pager(op), False


def _messaging_wedge_surface(mb: MessagingBriefAssetShapeContract) -> tuple[str, bool]:
    cf = (mb.category_frame or "").strip()
    pain0 = (mb.pains[0] or "").strip()[:360] if mb.pains else ""
    surf = " ".join([cf, pain0]).strip()
    if len(surf) >= _MIN_WEDGE_SURFACE:
        return surf, True
    return _blob_messaging(mb), False


def _cep_wedge_surface(ce: ChannelExecutionStructuredPayload) -> tuple[str, bool]:
    if not ce.prioritized_channels:
        return "", False
    parts: list[str] = []
    for ch in ce.prioritized_channels[:3]:
        parts.append((ch.objective or "")[:520])
        parts.append((ch.message_emphasis or "")[:520])
    surf = " ".join(parts).strip()
    if len(surf) >= _MIN_WEDGE_SURFACE:
        return surf, True
    return _blob_cep(ce), False


def _cep_gtm_surface(ce: ChannelExecutionStructuredPayload) -> str:
    parts: list[str] = []
    for ch in ce.prioritized_channels[:4]:
        parts.extend([(ch.objective or ""), (ch.message_emphasis or "")])
    return " ".join(parts).strip()


def _artifact_metric_surfaces(
    *,
    op: OnePagerStructuredPayload | None,
    mb: MessagingBriefAssetShapeContract | None,
    ce: ChannelExecutionStructuredPayload | None,
) -> list[str]:
    """Narrow surfaces that carry operational proof/metric cadence."""
    surfaces: list[str] = []
    if op:
        proofs = list(op.proof_highlights or [])
        if op.buying_trigger:
            proofs.append(op.buying_trigger[:480])
        s = " ".join(proofs).strip()
        if s:
            surfaces.append(s)
    if mb and mb.proof_points:
        s = " ".join(mb.proof_points).strip()
        if s:
            surfaces.append(s)
    if ce:
        proofs_ce: list[str] = []
        for ch in ce.prioritized_channels[:6]:
            proofs_ce.append(ch.proof_needed or "")
            proofs_ce.append(ch.success_signal or "")
        s = " ".join(proofs_ce).strip()
        if s:
            surfaces.append(s)
    return surfaces


def evaluate_cross_artifact_consistency(
    *,
    approved_pmm_strategy: ApprovedPMMStrategy,
    one_pager: OnePagerStructuredPayload | None = None,
    channel_execution: ChannelExecutionStructuredPayload | None = None,
    messaging_brief: MessagingBriefAssetShapeContract | None = None,
    coherence_report: ApprovedPMMStrategyCoherenceReport | None = None,
    artifact_type: str = "bundle",
    strategy_decision: StrategyBriefStructuredPayload | None = None,
) -> CrossArtifactConsistencyReport:
    _ = artifact_type
    pmm = approved_pmm_strategy
    coh = coherence_report or pmm.coherence_report
    present = _present(one_pager=one_pager, messaging_brief=messaging_brief, channel_execution=channel_execution)
    if len(present) < 2:
        return CrossArtifactConsistencyReport(
            overall_consistency_score=0.82,
            wedge_alignment_score=0.82,
            positioning_alignment_score=0.82,
            icp_alignment_score=0.82,
            pain_alignment_score=0.82,
            proof_alignment_score=0.82,
            contrast_alignment_score=0.82,
            gtm_alignment_score=0.82,
            metric_alignment_score=0.82,
            buyer_language_alignment_score=0.82,
            omission_flags=[f"insufficient_artifacts_for_cross_check:have={sorted(present)}"],
            artifact_pair_notes={"bundle": "Fewer than two artifacts supplied; scores neutralized."},
        )

    pw = _tok(pmm.strategic_wedge)
    pp = _tok(pmm.positioning_frame)
    picp = _tok(pmm.icp_primary)
    pproof = _tok(" ".join(pmm.proof_points))
    pcon = _tok(" ".join(c.contrast_claim for c in pmm.competitive_contrasts))
    pmet = _metric_reference_tokens(pmm, strategy_decision)
    pgtm = _tok(pmm.gtm_motion)

    op_b = _blob_one_pager(one_pager) if one_pager else ""
    mb_b = _blob_messaging(messaging_brief) if messaging_brief else ""
    ce_b = _blob_cep(channel_execution) if channel_execution else ""

    if one_pager:
        surf_w, _okw = _one_pager_wedge_surface(one_pager)
        wedge_op = _wedge_score_surface(surf_w, pw, pp)
    else:
        wedge_op = 0.88

    if messaging_brief:
        surf_wm, _okwm = _messaging_wedge_surface(messaging_brief)
        wedge_mb = _wedge_score_surface(surf_wm, pw, pp)
    else:
        wedge_mb = 0.88

    if channel_execution:
        surf_wc, _okwc = _cep_wedge_surface(channel_execution)
        wedge_ce = _wedge_score_surface(surf_wc, pw, pp)
        if ce_b.strip():
            t = _tok(ce_b)
            union = pw | pp
            if len(t & union) >= 3:
                wedge_ce = max(wedge_ce, 0.58)
    else:
        wedge_ce = 0.88

    w_vals = [
        v
        for v, ok in (
            (wedge_op, one_pager is not None),
            (wedge_mb, messaging_brief is not None),
            (wedge_ce, channel_execution is not None),
        )
        if ok
    ]
    wedge_alignment = sum(w_vals) / len(w_vals) if w_vals else 0.88

    if one_pager:
        surf_p, canon_p = _one_pager_positioning_surface(one_pager)
        pos_op = _positioning_score_to_pp(
            surface=surf_p,
            category=one_pager.category_line or "",
            positioning=one_pager.product_definition or "",
            pp=pp,
            use_full_blob_fallback=op_b if not canon_p else "",
        )
    else:
        pos_op = 0.88

    if messaging_brief:
        surf_m, canon_m = _messaging_positioning_surface(messaging_brief)
        pos_mb = _positioning_score_to_pp(
            surface=surf_m,
            category=messaging_brief.category_frame or "",
            positioning=messaging_brief.positioning or "",
            pp=pp,
            use_full_blob_fallback=mb_b if not canon_m else "",
        )
    else:
        pos_mb = 0.88

    positioning_alignment = min(pos_op, pos_mb) if messaging_brief and one_pager else max(pos_op, pos_mb)

    icp_op = _jac(_tok(one_pager.target_buyer_summary if one_pager else ""), picp) if one_pager else 0.88
    icp_mb = _jac(_tok(messaging_brief.icp if messaging_brief else ""), picp) if messaging_brief else 0.88
    icp_alignment = min(icp_op, icp_mb) if one_pager and messaging_brief else max(icp_op, icp_mb)

    pain_full = _jac(_tok(one_pager.problem_statement if one_pager else ""), _tok(" ".join(pmm.top_pain_points))) if one_pager else 0.88
    pain_lead_op = (
        _jac(_tok((one_pager.problem_statement or "")[:420]), _tok(" ".join(pmm.top_pain_points))) if one_pager else 0.88
    )
    pain_op = max(pain_full, pain_lead_op) if one_pager else 0.88

    pain_mb_full = _jac(_tok(" ".join(messaging_brief.pains if messaging_brief else [])), _tok(" ".join(pmm.top_pain_points))) if messaging_brief else 0.88
    pain_lead_mb = (
        _jac(
            _tok((messaging_brief.pains[0] if messaging_brief and messaging_brief.pains else "")[:400]),
            _tok(" ".join(pmm.top_pain_points)),
        )
        if messaging_brief
        else 0.88
    )
    pain_mb = max(pain_mb_full, pain_lead_mb) if messaging_brief else 0.88
    pain_alignment = min(pain_op, pain_mb) if one_pager and messaging_brief else max(pain_op, pain_mb)

    proof_op = _jac(_tok(" ".join(one_pager.proof_highlights if one_pager else [])), pproof) if one_pager else 0.88
    proof_mb = _jac(_tok(" ".join(messaging_brief.proof_points if messaging_brief else [])), pproof) if messaging_brief else 0.88
    proof_alignment = min(proof_op, proof_mb) if one_pager and messaging_brief else max(proof_op, proof_mb)

    diff_op = _jac(_tok(" ".join(one_pager.differentiators if one_pager else [])), pcon) if one_pager else 0.88
    diff_mb = _jac(_tok(" ".join(messaging_brief.differentiation if messaging_brief else [])), pcon) if messaging_brief else 0.88
    contrast_alignment = min(diff_op, diff_mb) if one_pager and messaging_brief else max(diff_op, diff_mb)

    gtm_alignment = 0.88
    if channel_execution and channel_execution.prioritized_channels:
        gtm_sur = _cep_gtm_surface(channel_execution)
        if len(gtm_sur) >= _MIN_GTM_SURFACE:
            j_n = _jac(_tok(gtm_sur), pgtm)
            j_b = _jac(_tok(ce_b), pgtm)
            gtm_alignment = max(0.0, min(1.0, 0.35 + 0.65 * max(j_n, j_b * 0.88)))
        else:
            gtm_alignment = max(0.0, min(1.0, 0.35 + 0.65 * _jac(_tok(ce_b), pgtm)))
    elif one_pager and messaging_brief:
        trig = (one_pager.buying_trigger or "").strip()
        wide = _jac(_tok((one_pager.cta or "") + (one_pager.buying_trigger or "")), pgtm)
        if len(trig) >= 16:
            jt = _jac(_tok(trig), pgtm)
            gtm_alignment = max(0.0, min(1.0, 0.4 + 0.6 * max(jt, wide * 0.9)))
        else:
            gtm_alignment = max(0.0, min(1.0, 0.4 + 0.6 * wide))

    narrow_metric_surfaces = _artifact_metric_surfaces(
        op=one_pager,
        mb=messaging_brief,
        ce=channel_execution,
    )
    if not pmet:
        metric_alignment = 0.9
        omission_flags_metric = ["metrics_absent_on_strategy_omission_ok"]
    else:
        nm_scores = [max(0.0, min(1.0, _jac(_tok(s), pmet))) for s in narrow_metric_surfaces if (s or "").strip()]
        if nm_scores:
            metric_alignment = max(0.0, min(1.0, sum(nm_scores) / len(nm_scores)))
            omission_flags_metric = []
        else:
            met_blobs = [op_b, mb_b]
            if channel_execution:
                met_blobs.append(ce_b)
            metric_alignment = max(
                0.0,
                min(1.0, sum(_jac(_tok(b), pmet) for b in met_blobs if b) / max(1, len([x for x in met_blobs if x]))),
            )
            omission_flags_metric = []

    tones_op = (_economic_density(op_b), _technical_density(op_b), _plg_density(op_b), _enterprise_density(op_b))
    tones_mb = (_economic_density(mb_b), _technical_density(mb_b), _plg_density(mb_b), _enterprise_density(mb_b))
    spread = max(abs(tones_op[i] - tones_mb[i]) for i in range(4)) if one_pager and messaging_brief else 0.0
    buyer_language_alignment = max(0.0, min(1.0, 1.0 - 0.45 * spread))

    notes: list[ArtifactAlignmentNote] = []
    pair_notes: dict[str, str] = {}
    contradictions: list[str] = []
    drifts: list[str] = []
    omissions: list[str] = list(omission_flags_metric)

    if one_pager and messaging_brief:
        if _economic_density(op_b) > 0.45 and _technical_density(mb_b) > 0.5 and _economic_density(mb_b) < 0.2:
            notes.append(
                ArtifactAlignmentNote(
                    artifact_a="one_pager",
                    artifact_b="messaging_brief",
                    dimension="wedge_commercial_bridge",
                    issue="One-pager emphasizes economics while messaging centers technical architecture without ROI bridge.",
                    severity=AlignmentSeverity.medium,
                    suggested_fix="Align messaging positioning clause with the same economic buyer outcome as the one-pager.",
                ),
            )
            drifts.append("economic_vs_technical_center_shift")
        if _jac(_tok(one_pager.category_line), _tok(messaging_brief.category_frame)) < 0.12:
            notes.append(
                ArtifactAlignmentNote(
                    artifact_a="one_pager",
                    artifact_b="messaging_brief",
                    dimension="positioning_category",
                    issue="Category / framing language diverges between one-pager and messaging brief.",
                    severity=AlignmentSeverity.medium,
                    suggested_fix="Normalize category line to ApprovedPMMStrategy.category_frame.",
                ),
            )
            drifts.append("category_frame_drift")
        pair_notes["one_pager_vs_messaging"] = f"positioning_jaccard≈{_jac(_tok(one_pager.category_line), _tok(messaging_brief.category_frame)):.2f}"
        pair_notes["positioning_score_mode"] = "canonical_fields_first_v1"
        pair_notes["metric_reference_mode"] = "strategy_proof_and_filtered_key_metrics" if strategy_decision else "proof_and_filtered_key_metrics"

    if channel_execution and one_pager:
        if _plg_density(ce_b) > 0.45 and _enterprise_density(op_b) > 0.35:
            notes.append(
                ArtifactAlignmentNote(
                    artifact_a="channel_execution",
                    artifact_b="one_pager",
                    dimension="gtm_motion",
                    issue="Channel plan emphasizes PLG-style motion while one-pager reads enterprise / committee-led.",
                    severity=AlignmentSeverity.high,
                    suggested_fix="Tighten channel objectives to reference the committed ApprovedPMMStrategy.gtm_motion verbatim where possible.",
                ),
            )
            contradictions.append("plg_channel_vs_enterprise_one_pager")

    if one_pager and messaging_brief:
        if proof_alignment < 0.22:
            omissions.append("proof_story_thin_across_assets")

    if coh and coh.overall_coherence_score >= 0.65:
        positioning_alignment = min(1.0, positioning_alignment + 0.04)

    overall = (
        0.12 * wedge_alignment
        + 0.12 * positioning_alignment
        + 0.1 * icp_alignment
        + 0.1 * pain_alignment
        + 0.12 * proof_alignment
        + 0.1 * contrast_alignment
        + 0.1 * gtm_alignment
        + 0.08 * metric_alignment
        + 0.1 * buyer_language_alignment
    )
    overall = max(0.0, min(1.0, overall - 0.06 * len(contradictions) - 0.03 * len(drifts)))

    suggestions: list[str] = []
    if drifts:
        suggestions.append("Run label normalization against ApprovedPMMStrategy category_frame and gtm_motion.")
    if contradictions:
        suggestions.append("Resolve high-severity GTM or commercial framing contradictions before external publish.")

    return CrossArtifactConsistencyReport(
        overall_consistency_score=round(overall, 4),
        wedge_alignment_score=round(wedge_alignment, 4),
        positioning_alignment_score=round(positioning_alignment, 4),
        icp_alignment_score=round(icp_alignment, 4),
        pain_alignment_score=round(pain_alignment, 4),
        proof_alignment_score=round(proof_alignment, 4),
        contrast_alignment_score=round(contrast_alignment, 4),
        gtm_alignment_score=round(gtm_alignment, 4),
        metric_alignment_score=round(metric_alignment, 4),
        buyer_language_alignment_score=round(buyer_language_alignment, 4),
        contradiction_flags=contradictions,
        drift_flags=drifts,
        omission_flags=omissions,
        normalization_suggestions=suggestions[:16],
        artifact_pair_notes=pair_notes,
        alignment_notes=notes[:24],
    )


def _harmonize_cep_plan_level_success_signals(
    cep: ChannelExecutionStructuredPayload,
    pmm: ApprovedPMMStrategy,
) -> tuple[ChannelExecutionStructuredPayload, list[str]]:
    """
    Case/spacing canonicalization of top-level success_signals to ApprovedPMMStrategy.key_metrics.
    Does not modify prioritized channel rows.
    """
    if not pmm.key_metrics:
        return cep, []
    canon = {m.strip().lower(): m.strip() for m in pmm.key_metrics if m and m.strip()}
    reasons: list[str] = []
    new_sigs: list[str] = []
    changed = False
    for sig in cep.success_signals:
        k = sig.strip().lower()
        if k in canon and sig != canon[k]:
            new_sigs.append(canon[k])
            changed = True
            reasons.append("cep_success_signal_canonicalized_to_pmm_key_metric")
        else:
            new_sigs.append(sig)
    if not changed:
        return cep, []
    return cep.model_copy(update={"success_signals": new_sigs}), reasons


def apply_cross_artifact_normalization(
    approved_pmm_strategy: ApprovedPMMStrategy,
    one_pager: OnePagerStructuredPayload | None,
    messaging_brief: MessagingBriefAssetShapeContract | None,
    channel_execution: ChannelExecutionStructuredPayload | None,
) -> tuple[
    OnePagerStructuredPayload | None,
    MessagingBriefAssetShapeContract | None,
    ChannelExecutionStructuredPayload | None,
    bool,
    str | None,
]:
    """
    Non-generative label sync to ApprovedPMMStrategy only. Does not add new claims.
    Returns (one_pager, messaging, channel, applied, reason).
    """
    reasons: list[str] = []
    applied = False
    pmm = approved_pmm_strategy
    op, mb, cep = one_pager, messaging_brief, channel_execution

    def cat_mismatch(a: str, b: str) -> bool:
        return _jac(_tok(a), _tok(b)) < 0.14 and min(len(a), len(b)) >= 12

    if op and cat_mismatch(op.category_line, pmm.category_frame):
        op = op.model_copy(update={"category_line": pmm.category_frame[:220]})
        reasons.append("one_pager_category_line_synced_to_pmm_category_frame")
        applied = True
    if mb and cat_mismatch(mb.category_frame, pmm.category_frame):
        mb = mb.model_copy(update={"category_frame": pmm.category_frame[:800]})
        reasons.append("messaging_category_frame_synced_to_pmm")
        applied = True

    if mb and _jac(_tok(mb.positioning), _tok(pmm.positioning_frame)) < 0.12:
        mb = mb.model_copy(update={"positioning": pmm.positioning_frame[:1200]})
        reasons.append("messaging_positioning_synced_to_pmm")
        applied = True

    if cep is not None:
        cep2, cep_rs = _harmonize_cep_plan_level_success_signals(cep, pmm)
        if cep_rs:
            cep = cep2
            applied = True
            reasons.extend(cep_rs)

    reason = ";".join(reasons) if reasons else None
    return op, mb, cep, applied, reason


def apply_cross_artifact_bundle_to_channel_execution_payload(
    *,
    channel_execution: ChannelExecutionStructuredPayload,
    approved_pmm_strategy: ApprovedPMMStrategy,
    peer_one_pager: OnePagerStructuredPayload | None = None,
    peer_messaging_brief: MessagingBriefAssetShapeContract | None = None,
    coherence_report: ApprovedPMMStrategyCoherenceReport | None = None,
    allow_normalization: bool = True,
    block_on_high_severity_contradiction: bool = False,
    strategy_decision: StrategyBriefStructuredPayload | None = None,
) -> ChannelExecutionStructuredPayload:
    """
    Cross-artifact consistency for CEP after per-artifact quality: optional peers, optional normalization,
    then channel row hard gates. Does not invent peer payloads.
    """
    if peer_one_pager is None and peer_messaging_brief is None:
        return channel_execution

    coh = coherence_report if coherence_report is not None else approved_pmm_strategy.coherence_report
    rep = evaluate_cross_artifact_consistency(
        approved_pmm_strategy=approved_pmm_strategy,
        one_pager=peer_one_pager,
        channel_execution=channel_execution,
        messaging_brief=peer_messaging_brief,
        coherence_report=coh,
        strategy_decision=strategy_decision,
    )
    try:
        enforce_cross_artifact_blocking_if_required(
            rep,
            block_on_high_severity_contradiction=block_on_high_severity_contradiction,
        )
    except CollateralFrameworkError as e:
        raise ChannelExecutionFrameworkError(e.status_code, e.detail) from e

    norm_applied = False
    norm_reason: str | None = None
    out_cep = channel_execution
    if allow_normalization:
        _op2, _mb2, cep2, norm_applied, norm_reason = apply_cross_artifact_normalization(
            approved_pmm_strategy,
            peer_one_pager,
            peer_messaging_brief,
            channel_execution,
        )
        out_cep = cep2 if cep2 is not None else channel_execution

    validate_channel_execution_payload_rows_against_pmm(out_cep, approved_pmm_strategy)

    rep_final = merge_cross_consistency_into_report(
        rep,
        normalization_applied=norm_applied,
        normalization_reason=norm_reason,
    )
    return out_cep.model_copy(
        update={
            "cross_artifact_consistency_report": rep_final,
            "cross_artifact_normalization_applied": norm_applied,
            "cross_artifact_normalization_reason": norm_reason,
        },
    )


def enforce_cross_artifact_blocking_if_required(
    report: CrossArtifactConsistencyReport,
    *,
    block_on_high_severity_contradiction: bool,
) -> None:
    if not block_on_high_severity_contradiction:
        return
    if any(n.severity == AlignmentSeverity.high for n in report.alignment_notes):
        raise CollateralFrameworkError(
            422,
            json.dumps(
                {
                    "error": "cross_artifact_consistency",
                    "message": "High-severity cross-artifact contradiction",
                    "report": report.model_dump(mode="json"),
                },
            ),
        )


def merge_cross_consistency_into_report(
    base: CrossArtifactConsistencyReport,
    *,
    normalization_applied: bool,
    normalization_reason: str | None,
) -> CrossArtifactConsistencyReport:
    return base.model_copy(
        update={
            "normalization_applied": normalization_applied,
            "normalization_reason": normalization_reason,
        },
    )
