"""Stage gates: deterministic checks every agent-written artifact must pass.

Agents write the artifacts (evidence, strategy brief, message spine). Nothing here calls a model.
Each gate validates the artifact against its stage contract, checks that every load-bearing field
cites admitted evidence of the right kind, and applies the craft rules recorded in docs/adr/0003.
A stage may only run when the stage before it has a passing gate report on disk.

Violations block. Warnings are recorded in the report and do not block.

Run layout (one directory per run):

    runs/<run>/evidence.json            written by the evidence skill
    runs/<run>/evidence.scored.json     written by the evidence gate (verification, origins, admission)
    runs/<run>/strategy_brief.json      written by the strategy-brief skill
    runs/<run>/message_spine.json       written by the message-spine skill
    runs/<run>/<stage>.gate.json        gate report for each stage
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from kaizen.canonical_assertion_contract import ClaimType
from kaizen.message_spine_contract import MessageSpineStructuredPayload
from kaizen.output_leakage_validator import (
    OutputValidationError,
    validate_no_research_leakage,
    validate_non_generic_strategy_language,
)
from kaizen.provenance_scoring import evaluate_provenance_layer
from kaizen.strategy_brief_contract import StrategyBriefStructuredPayload

GATE_VERSION = "2.0"

STAGES: tuple[str, ...] = ("research", "evidence", "strategy_brief", "message_spine")
# Research is optional: evidence waits for it only when the run has a research plan.
UPSTREAM: dict[str, str | None] = {
    "research": None,
    "evidence": "research",
    "strategy_brief": "evidence",
    "message_spine": "strategy_brief",
}

MIN_ADMITTED_CLAIMS = 6
MIN_QUOTE_CHARS = 20
# Three or more promotional markers (0.086 each in provenance_scoring) mark an undeclared promotional source.
PROMOTIONAL_PENALTY = 0.25
# Two documents sharing this many 8-word sequences are treated as one origin (one rewrites the other).
SHARED_SHINGLES_FOR_SAME_ORIGIN = 3
SHINGLE_WORDS = 8
STALE_AFTER_DAYS = 730

STRATEGY_CITED_FIELDS = (
    "strategic_recommendation",
    "recommended_icp",
    "problem_frame",
    "wedge",
    "differentiation_claim",
    "proof_requirements",
    "preferred_gtm_motion",
)
# Load-bearing claims that need independent corroboration.
TWO_ORIGIN_FIELDS = ("problem_frame", "differentiation_claim")
# Prevalence claims also need more than one research method (survivorship guard).
TWO_METHOD_FIELDS = ("problem_frame",)
MIN_ORIGINS = 2
MIN_METHODS = 2
COMMITMENT_FIELDS = ("strategic_recommendation", "recommended_icp", "wedge", "preferred_gtm_motion")
SPINE_CITED_FIELDS = ("proof_points", "objection_map")
MAX_PILLARS = 4

Section = Literal[
    "market_overview",
    "key_problems",
    "buyer_segments",
    "competitive_landscape",
    "emerging_signals",
    "risks_and_uncertainties",
]


class EvidenceKind(StrEnum):
    """What the quote actually shows. Ordered from strongest to weakest."""

    observed_behavior = "observed_behavior"  # what someone did, observed or recorded
    past_episode = "past_episode"  # a specific past event the speaker took part in
    market_data = "market_data"  # a measured figure from an independent study
    stated_preference = "stated_preference"  # what someone says they want or value
    prediction = "prediction"  # what someone says they would do
    vendor_claim = "vendor_claim"  # what a vendor or competitor says about itself or the market


STRONG_KINDS = frozenset({EvidenceKind.observed_behavior, EvidenceKind.past_episode, EvidenceKind.market_data})
BEHAVIOR_KINDS = frozenset({EvidenceKind.observed_behavior, EvidenceKind.past_episode})


class AlternativeType(StrEnum):
    vendor = "vendor"
    status_quo = "status_quo"
    diy = "diy"
    outsourced = "outsourced"
    in_house_build = "in_house_build"
    other = "other"


VENDOR_RELATIONS = frozenset({"vendor", "competitor", "sponsored"})
AUTHOR_RELATIONS = frozenset({"first_party", "independent"}) | VENDOR_RELATIONS

# "could" is left out on purpose: in reported speech it is usually past ability ("nobody could say
# who approved it"), and flagging it pushed an agent to cut a factual sentence from a quote.
_HYPOTHETICAL = re.compile(r"\b(would|will|might|always|usually|never)\b|\bif we\b", re.I)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_HEDGES = re.compile(
    r"\b(could|might|perhaps|possibly|consider|explore)\b|options include|one approach",
    re.I,
)
_ICP_SPLIT = re.compile(r"\band/or\b|\bas well as\b|\bboth\b.{1,60}\band\b", re.I)
_SUPERLATIVES = (
    "best-in-class",
    "best in class",
    "world-class",
    "seamless",
    "all-in-one",
    "cutting-edge",
    "next-generation",
    "industry-leading",
    "game-changing",
    "revolutionary",
)
_SUPPORT_WORDING = re.compile(
    r"\bproven\b|\bstudies show\b|\bdata shows\b|\bresearch shows\b|\d\s*%|\b\d+(?:\.\d+)?x\b|\btimes faster\b",
    re.I,
)


# --------------------------------------------------------------------------------------------
# Reports


@dataclass
class Violation:
    code: str
    detail: str


@dataclass
class GateReport:
    stage: str
    passed: bool = True
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def fail(self, code: str, detail: str) -> None:
        self.passed = False
        self.violations.append(Violation(code, detail))

    def warn(self, code: str, detail: str) -> None:
        self.warnings.append(Violation(code, detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_version": GATE_VERSION,
            "stage": self.stage,
            "passed": self.passed,
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "violations": [{"code": v.code, "detail": v.detail} for v in self.violations],
            "warnings": [{"code": v.code, "detail": v.detail} for v in self.warnings],
            "metrics": self.metrics,
        }


# --------------------------------------------------------------------------------------------
# Text helpers

_STOP = frozenset(
    "a an and are as at be but by for from has have in into is it its of on or our that the their them "
    "they this to was we were what when which who will with without not than then so can more most your "
    "you any all each every one".split(),
)
_QUOTE_CHARS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def _norm(text: str) -> str:
    t = text.translate(_QUOTE_CHARS)
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()) if w not in _STOP}


def _jaccard(a: str, b: str) -> float:
    x, y = _words(a), _words(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def _numbers(text: str) -> set[str]:
    """Factual numbers in a text. Evidence ids (E01) are references, not figures."""
    text = re.sub(r"\bE\d{2,3}\b", " ", text)
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def _text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_text_of(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text_of(v) for v in value)
    return ""


# --------------------------------------------------------------------------------------------
# Corpus

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


@dataclass(frozen=True)
class CorpusDoc:
    name: str
    meta: dict[str, str]
    body: str

    @property
    def source_type(self) -> str:
        return self.meta.get("source_type", "_")


def load_corpus(corpus_dir: Path) -> dict[str, CorpusDoc]:
    docs: dict[str, CorpusDoc] = {}
    for p in sorted(corpus_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        text = p.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        m = _FRONTMATTER.match(text)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            text = text[m.end() :]
        docs[p.name] = CorpusDoc(p.name, meta, text)
    return docs


def promotional_penalty(doc: CorpusDoc) -> float:
    envelope = {
        "source_type": doc.source_type,
        "source_platform": doc.meta.get("source_platform", ""),
        "author_type": doc.meta.get("author_type", "unknown"),
        "channel_or_community": doc.meta.get("channel_or_community", ""),
        "title": doc.meta.get("title", ""),
    }
    r = evaluate_provenance_layer({"text": doc.body, "source_provenance": envelope})
    return round(r.promotional_risk_penalty or 0.0, 3)


def author_relation(doc: CorpusDoc, penalty: float) -> str:
    """Declared relation, overridden to 'sponsored' when the text itself is promotional."""
    declared = doc.meta.get("author_relation", "").strip().lower()
    if penalty >= PROMOTIONAL_PENALTY and declared not in VENDOR_RELATIONS:
        return "sponsored"
    return declared or "independent"


def _shingles(text: str) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(w[i : i + SHINGLE_WORDS]) for i in range(max(0, len(w) - SHINGLE_WORDS + 1))}


def origins(docs: dict[str, CorpusDoc]) -> dict[str, str]:
    """Map each document to an origin id. Documents that share long passages share an origin."""
    names = sorted(docs)
    parent = {n: n for n in names}

    def find(n: str) -> str:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    sh = {n: _shingles(docs[n].body) for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if len(sh[a] & sh[b]) >= SHARED_SHINGLES_FOR_SAME_ORIGIN:
                parent[find(b)] = find(a)
    return {n: find(n) for n in names}


def _published(doc: CorpusDoc) -> datetime | None:
    try:
        return datetime.fromisoformat(doc.meta.get("published", "")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------
# Evidence stage


class EvidenceClaim(BaseModel):
    """One claim the evidence agent extracted. No score fields: weighing evidence is the gate's job."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., pattern=r"^E\d{2,3}$")
    claim: str = Field(..., min_length=12, max_length=600)
    quote: str = Field(..., min_length=MIN_QUOTE_CHARS, max_length=600)
    doc: str = Field(..., min_length=4)
    section: Section
    claim_type: ClaimType
    evidence_kind: EvidenceKind
    alternative: str | None = Field(default=None, min_length=2, max_length=120)
    alternative_type: AlternativeType | None = None

    @model_validator(mode="after")
    def _alternative_pair(self) -> EvidenceClaim:
        if (self.alternative is None) != (self.alternative_type is None):
            raise ValueError("alternative and alternative_type must be set together")
        return self


class EvidenceFile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_version: str = "2.0"
    corpus: str
    claims: list[EvidenceClaim] = Field(..., min_length=1)


def gate_evidence(run_dir: Path, repo_root: Path) -> GateReport:
    report = GateReport("evidence")
    path = run_dir / "evidence.json"
    try:
        ev = EvidenceFile.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.fail("missing_artifact", str(path))
        return report
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            report.fail("contract_violation", f"{loc}: {err['msg']}")
        return report

    docs = load_corpus((repo_root / ev.corpus).resolve())
    if not docs:
        report.fail("empty_corpus", ev.corpus)
        return report

    penalty = {n: promotional_penalty(d) for n, d in docs.items()}
    relation = {n: author_relation(d, penalty[n]) for n, d in docs.items()}
    origin = origins(docs)

    dated = [d for d in (_published(x) for x in docs.values()) if d is not None]
    newest = max(dated) if dated else None
    sources: dict[str, Any] = {}
    for n, d in docs.items():
        pub = _published(d)
        declared = d.meta.get("author_relation", "").strip().lower()
        if declared and declared not in AUTHOR_RELATIONS:
            report.fail("unknown_author_relation", f"{n}: {declared}")
        if declared not in VENDOR_RELATIONS and relation[n] == "sponsored":
            report.warn("undeclared_promotional_source", f"{n}: promotional penalty {penalty[n]}, treated as sponsored")
        if pub is None:
            report.warn("undated_source", n)
        elif newest is not None and (newest - pub).days > STALE_AFTER_DAYS:
            report.warn("stale_source", f"{n}: {(newest - pub).days} days older than the newest source")
        sources[n] = {
            "source_type": d.source_type,
            "author_relation": relation[n],
            "origin": origin[n],
            "promotional_penalty": penalty[n],
            "published": d.meta.get("published"),
        }

    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for c in ev.claims:
        if c.id in seen:
            report.fail("duplicate_id", c.id)
            continue
        seen.add(c.id)
        doc = docs.get(c.doc)
        if doc is None:
            report.fail("unknown_doc", f"{c.id} cites {c.doc}")
            continue
        issues: list[tuple[str, str]] = []
        if _norm(c.quote) not in _norm(doc.body):
            issues.append(("quote_not_in_source", f"{c.id}: quote not found verbatim in {c.doc}"))
        missing = _numbers(c.claim) - _numbers(c.quote)
        if missing:
            issues.append(("number_not_in_quote", f"{c.id}: {', '.join(sorted(missing))} not in the quote"))
        if c.evidence_kind in BEHAVIOR_KINDS and _HYPOTHETICAL.search(c.quote):
            word = _HYPOTHETICAL.search(c.quote).group(0)
            issues.append(
                ("hypothetical_tagged_as_behavior", f"{c.id}: quote says '{word}' but is tagged {c.evidence_kind}"),
            )
        if relation[c.doc] in VENDOR_RELATIONS and c.evidence_kind != EvidenceKind.vendor_claim:
            issues.append(
                ("vendor_source_not_vendor_claim", f"{c.id}: {c.doc} is {relation[c.doc]}; tag it vendor_claim"),
            )
        for code, detail in issues:
            report.fail(code, detail)
        scored.append(
            {
                "id": c.id,
                "claim": c.claim,
                "quote": c.quote,
                "doc": c.doc,
                "section": c.section,
                "claim_type": str(c.claim_type),
                "evidence_kind": str(c.evidence_kind),
                "alternative": c.alternative,
                "alternative_type": str(c.alternative_type) if c.alternative_type else None,
                "source_type": doc.source_type,
                "author_relation": relation[c.doc],
                "origin": origin[c.doc],
                "admitted": not issues,
            },
        )

    admitted = [s for s in scored if s["admitted"]]
    independent = [s for s in admitted if s["evidence_kind"] != EvidenceKind.vendor_claim]
    kinds: dict[str, int] = {}
    for s in admitted:
        kinds[s["evidence_kind"]] = kinds.get(s["evidence_kind"], 0) + 1
    report.metrics = {
        "claims": len(ev.claims),
        "admitted": len(admitted),
        "vendor_claims": len(admitted) - len(independent),
        "evidence_kinds": dict(sorted(kinds.items())),
        "documents": len(docs),
        "independent_origins": len(set(origin.values())),
        "research_methods": len({d.source_type for d in docs.values()}),
    }
    if len(independent) < MIN_ADMITTED_CLAIMS:
        report.fail(
            "too_little_admitted_evidence",
            f"{len(independent)} admitted non-vendor claims, need {MIN_ADMITTED_CLAIMS}",
        )

    (run_dir / "evidence.scored.json").write_text(
        json.dumps({"corpus": ev.corpus, "sources": sources, "claims": scored}, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def load_evidence(run_dir: Path) -> dict[str, dict[str, Any]]:
    data = json.loads((run_dir / "evidence.scored.json").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["claims"]}


# --------------------------------------------------------------------------------------------
# Shared by the downstream stages


class StageArtifact(BaseModel):
    """Envelope for downstream stages. Citation keys are a payload field or field.index."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    payload: dict[str, Any]
    citations: dict[str, list[str]] = Field(default_factory=dict)


def _cited(art: StageArtifact, key: str, evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [evidence[e] for e in art.citations.get(key, []) if e in evidence and evidence[e]["admitted"]]


def _check_citation_ids(report: GateReport, art: StageArtifact, evidence: dict[str, dict[str, Any]]) -> None:
    for key, ids in art.citations.items():
        base, _, idx = key.partition(".")
        if base not in art.payload:
            report.fail("citation_for_unknown_field", key)
        elif idx:
            items = art.payload.get(base)
            if not idx.isdigit() or not isinstance(items, list) or int(idx) >= len(items):
                report.fail("citation_for_unknown_field", key)
        for eid in ids:
            e = evidence.get(eid)
            if e is None:
                report.fail("unknown_evidence", f"{key} cites {eid}")
            elif not e["admitted"]:
                report.fail("cites_unadmitted_evidence", f"{key} cites {eid}")


def _require_cited(report: GateReport, art: StageArtifact, keys: tuple[str, ...]) -> None:
    for k in keys:
        if not art.citations.get(k):
            report.fail("uncited_field", k)


def _check_language(report: GateReport, payload: dict[str, Any]) -> None:
    for check in (validate_no_research_leakage, validate_non_generic_strategy_language):
        try:
            check(payload)
        except OutputValidationError as e:
            for v in e.violations:
                report.fail(v.code, v.detail)
    low = _text_of(payload).lower()
    for phrase in _SUPERLATIVES:
        if phrase in low:
            report.fail("superlative_or_sameness", phrase)


def _load_stage(run_dir: Path, stage: str, report: GateReport) -> StageArtifact | None:
    path = run_dir / f"{stage}.json"
    try:
        art = StageArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.fail("missing_artifact", str(path))
        return None
    except ValidationError as e:
        report.fail("envelope_violation", str(e.errors()[0]["msg"]))
        return None
    if art.stage != stage:
        report.fail("wrong_stage", f"envelope says {art.stage}")
    return art


def _contract(report: GateReport, model: type[BaseModel], payload: dict[str, Any]) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            report.fail("contract_violation", f"{loc}: {err['msg']}")
        return None


# --------------------------------------------------------------------------------------------
# Strategy brief


def gate_strategy_brief(run_dir: Path, repo_root: Path) -> GateReport:
    _ = repo_root
    report = GateReport("strategy_brief")
    art = _load_stage(run_dir, "strategy_brief", report)
    if art is None:
        return report
    sb: StrategyBriefStructuredPayload | None = _contract(report, StrategyBriefStructuredPayload, art.payload)
    evidence = load_evidence(run_dir)
    _check_citation_ids(report, art, evidence)
    _require_cited(report, art, STRATEGY_CITED_FIELDS)

    # Fact, not someone else's recommendation, under every load-bearing field.
    for f in STRATEGY_CITED_FIELDS:
        cited = _cited(art, f, evidence)
        if cited and all(e["claim_type"] == "recommendation" for e in cited):
            report.fail("rests_only_on_recommendations", f)

    # Strength, independent corroboration and method triangulation.
    for f in TWO_ORIGIN_FIELDS:
        cited = [e for e in _cited(art, f, evidence) if e["evidence_kind"] != EvidenceKind.vendor_claim]
        if not any(e["evidence_kind"] in STRONG_KINDS for e in cited):
            report.fail("no_behavioral_or_market_evidence", f"{f} cites only stated preferences, predictions or vendor claims")
        n_origins = len({e["origin"] for e in cited})
        report.metrics[f"{f}_origins"] = n_origins
        if n_origins < MIN_ORIGINS:
            report.fail("single_origin_claim", f"{f} rests on {n_origins} independent origin(s); needs {MIN_ORIGINS}")
    for f in TWO_METHOD_FIELDS:
        cited = [e for e in _cited(art, f, evidence) if e["evidence_kind"] != EvidenceKind.vendor_claim]
        n_methods = len({e["source_type"] for e in cited})
        report.metrics[f"{f}_methods"] = n_methods
        if n_methods < MIN_METHODS:
            report.fail("single_method_claim", f"{f} draws on {n_methods} research method(s); needs {MIN_METHODS}")

    if sb is not None:
        # Differentiation names an alternative the evidence actually shows buyers considering.
        alternatives = {
            e["alternative"].lower()
            for e in evidence.values()
            if e["admitted"] and e["section"] == "competitive_landscape" and e["alternative"]
        }
        diff = sb.differentiation_claim.lower()
        if not any(a in diff for a in alternatives):
            report.fail("differentiation_names_no_alternative", "name an alternative from admitted competitive evidence")
        if not any(e["section"] == "competitive_landscape" for e in _cited(art, "differentiation_claim", evidence)):
            report.fail("differentiation_without_competitive_evidence", "cite competitive_landscape evidence")

        # Exclusions carry a reason and evidence that they were real options.
        all_cited = [e for ids in art.citations.values() for e in ids]
        for group in ("excluded_icps", "rejected_gtm_motions"):
            for i, x in enumerate(getattr(sb, group)):
                for eid in x.evidence:
                    e = evidence.get(eid)
                    if e is None or not e["admitted"]:
                        report.fail("exclusion_evidence_invalid", f"{group}.{i} cites {eid}")
                all_cited += x.evidence

        # The status quo or a do-it-yourself option is considered somewhere in the brief.
        types = {evidence[e]["alternative_type"] for e in all_cited if e in evidence}
        if not types & {"status_quo", "diy"}:
            report.fail("status_quo_not_considered", "cite evidence on the status quo or a do-it-yourself alternative")

        # Committed language and a single target.
        for f in COMMITMENT_FIELDS:
            m = _HEDGES.search(getattr(sb, f))
            if m:
                report.fail("hedged_commitment", f"{f}: '{m.group(0)}'")
        m = _ICP_SPLIT.search(sb.recommended_icp)
        if m:
            report.fail("icp_not_singular", f"recommended_icp joins segments: '{m.group(0)}'")
        for x in sb.excluded_icps:
            if _jaccard(x.item, sb.recommended_icp) >= 0.6:
                report.fail("icp_overlaps_exclusion", x.item)

        # Non-blocking coherence checks.
        anchor = " ".join(sb.key_adoption_blockers + sb.strategic_risks + sb.proof_requirements)
        for i, move in enumerate(sb.immediate_next_strategic_moves):
            if len(_words(move) & _words(anchor)) < 2:
                report.warn("move_not_linked", f"immediate_next_strategic_moves.{i} shares no key terms with blockers, risks or proof")
        if sb.category_style == "new":
            report.warn("category_creation", "new category: the hardest style; prove buyers recognize the problem first")

    _check_language(report, art.payload)
    report.metrics["cited_evidence"] = len({e for ids in art.citations.values() for e in ids})
    return report


# --------------------------------------------------------------------------------------------
# Message spine


def _head_noun(category_frame: str) -> str:
    """Last content word before the first qualifier: 'Approval control layer for X' -> 'layer'."""
    t = re.split(r"\s[-–—]\s|[;,:]", category_frame, maxsplit=1)[0]
    t = re.split(r"\b(?:for|that|of|on|to|in|which|with|over)\b", t, maxsplit=1)[0]
    words = [w for w in re.findall(r"[a-z][a-z0-9-]+", t.lower()) if w not in _STOP]
    return words[-1] if words else ""


def gate_message_spine(run_dir: Path, repo_root: Path) -> GateReport:
    _ = repo_root
    report = GateReport("message_spine")
    art = _load_stage(run_dir, "message_spine", report)
    if art is None:
        return report
    spine: MessageSpineStructuredPayload | None = _contract(report, MessageSpineStructuredPayload, art.payload)
    evidence = load_evidence(run_dir)
    _check_citation_ids(report, art, evidence)
    _require_cited(report, art, SPINE_CITED_FIELDS)
    sb = StrategyBriefStructuredPayload.model_validate(
        json.loads((run_dir / "strategy_brief.json").read_text(encoding="utf-8"))["payload"],
    )

    if spine is not None:
        pillars = spine.value_pillars
        # Pillars: few, distinct, each with cited proof.
        if len(pillars) > MAX_PILLARS:
            report.fail("too_many_pillars", f"{len(pillars)} pillars; keep 1 to {MAX_PILLARS}")
        for i, p in enumerate(pillars):
            if not _cited(art, f"value_pillars.{i}", evidence):
                report.fail("pillar_without_proof", f"value_pillars.{i}: cite admitted evidence as value_pillars.{i}")
            for j in range(i + 1, len(pillars)):
                if _jaccard(p, pillars[j]) >= 0.5:
                    report.fail("duplicate_pillars", f"value_pillars.{i} and value_pillars.{j}")

        # Personas: each with cited proof, none from the excluded ICPs.
        for i, row in enumerate(spine.persona_message_hierarchy):
            if not row.supporting_proof.strip() or not _cited(art, f"persona_message_hierarchy.{i}", evidence):
                report.fail("persona_without_proof", f"persona_message_hierarchy.{i}")
            for x in sb.excluded_icps:
                if _jaccard(row.persona, x.item) >= 0.6:
                    report.fail("persona_is_excluded_icp", f"persona_message_hierarchy.{i}: {x.item}")

        # Wording that claims support must cite behavioral or market evidence.
        units: list[tuple[str, str]] = [
            ("master_narrative", spine.master_narrative),
            ("category_statement", spine.category_statement),
            ("wedge_expression", spine.wedge_expression),
        ]
        for fname in ("value_pillars", "proof_points", "objection_map", "cta_logic"):
            units += [(f"{fname}.{i}", t) for i, t in enumerate(getattr(spine, fname))]
        units += [
            (f"persona_message_hierarchy.{i}", f"{r.headline} {r.supporting_proof}")
            for i, r in enumerate(spine.persona_message_hierarchy)
        ]
        for key, text in units:
            m = _SUPPORT_WORDING.search(text)
            if not m:
                continue
            cited = _cited(art, key, evidence) or _cited(art, key.split(".")[0], evidence)
            if not any(e["evidence_kind"] in STRONG_KINDS for e in cited):
                report.fail("unsubstantiated_claim", f"{key}: '{m.group(0)}' needs behavioral or market evidence")

        # Every proof requirement in the strategy has a proof point.
        for i, req in enumerate(sb.proof_requirements):
            if not any(len(_words(req) & _words(p)) >= 2 for p in spine.proof_points):
                report.fail("proof_requirement_unmapped", f"strategy proof_requirements.{i} has no matching proof point")

        # The call to action does not run a rejected motion.
        for x in sb.rejected_gtm_motions:
            core = _words(x.item)
            if len(core) < 3:
                continue
            for i, cta in enumerate(spine.cta_logic):
                if len(core & _words(cta)) / len(core) >= 0.6:
                    report.fail("cta_uses_rejected_motion", f"cta_logic.{i} ~ '{x.item}'")

        # Anchors to the strategy, in place of word-overlap scoring.
        head = _head_noun(sb.category_frame)
        report.metrics["category_head_noun"] = head
        if head and head not in spine.category_statement.lower():
            report.fail("category_anchor_missing", f"category_statement does not carry '{head}' from category_frame")
        wedge_terms = {w for w in _words(sb.wedge) if len(w) >= 4}
        best = max((len(wedge_terms & _words(p)) for p in pillars), default=0)
        report.metrics["wedge_terms_in_best_pillar"] = best
        if best < 2:
            report.fail("wedge_anchor_missing", "no value pillar carries two key terms of the strategy's wedge")
        icp_shared = len(_words(sb.recommended_icp) & _words(spine.persona_message_hierarchy[0].persona))
        report.metrics["icp_terms_in_first_persona"] = icp_shared
        if icp_shared < 2:
            report.fail("icp_anchor_missing", "the first persona is not the strategy's recommended ICP")

        spoken = _text_of(
            [spine.master_narrative, spine.category_statement, spine.wedge_expression, pillars]
            + [r.headline for r in spine.persona_message_hierarchy],
        ).lower()
        for phrase in spine.forbidden_language:
            p = phrase.strip().lower().strip('"')
            if len(p) >= 4 and p in spoken:
                report.fail("uses_own_forbidden_language", phrase)

    _check_language(report, art.payload)
    return report


# --------------------------------------------------------------------------------------------
# Research


MIN_RESEARCH_DOCS = 5
MIN_RESEARCH_DOMAINS = 3


class ResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    file: str = Field(..., min_length=4)
    question: str = Field(..., min_length=12, description="Which research question this source answers.")


class ResearchPlan(BaseModel):
    """What the research agent writes. It names questions, queries and sources; it never holds page text."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stage: Literal["research"]
    questions: list[str] = Field(..., min_length=1)
    queries: list[str] = Field(..., min_length=1)
    sources: list[ResearchSource] = Field(..., min_length=1)


def gate_research(run_dir: Path, repo_root: Path) -> GateReport:
    from kaizen.fetch import AUTHOR_RELATIONS as FETCH_RELATIONS
    from kaizen.fetch import SOURCE_TYPES, body_hash, load_manifest

    _ = repo_root
    report = GateReport("research")
    path = run_dir / "research.json"
    try:
        plan = ResearchPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.fail("missing_artifact", str(path))
        return report
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            report.fail("contract_violation", f"{loc}: {err['msg']}")
        return report

    corpus = run_dir / "corpus"
    manifest = load_manifest(corpus)
    docs = load_corpus(corpus)

    # Integrity: every document was written by the fetcher and is unchanged since.
    for name, doc in docs.items():
        entry = manifest.get(name)
        if entry is None:
            report.fail("unmanifested_document", f"{name} was not written by the fetcher")
        elif body_hash(doc.body) != entry["sha256"]:
            report.fail("document_modified", f"{name} changed after it was fetched")
    for name in manifest:
        if name not in docs:
            report.fail("missing_document", name)

    # Every source is declared, and a vendor's own page is never labelled independent.
    for name, doc in docs.items():
        st = doc.meta.get("source_type", "")
        rel = doc.meta.get("author_relation", "")
        if st not in SOURCE_TYPES or rel not in FETCH_RELATIONS:
            report.fail("undeclared_source", f"{name}: source_type={st or '?'} author_relation={rel or '?'}")
        if st == "vendor_page" and rel not in VENDOR_RELATIONS:
            report.fail("vendor_page_not_vendor", f"{name}: a vendor page must be vendor, competitor or sponsored")
        pen = promotional_penalty(doc)
        if pen >= PROMOTIONAL_PENALTY and rel not in VENDOR_RELATIONS:
            report.warn("promotional_source_marked_independent", f"{name}: penalty {pen}; the evidence gate will treat it as sponsored")
        if "published" not in doc.meta:
            report.warn("undated_source", f"{name}: the page carries no publication date")
        url = (manifest.get(name) or {}).get("url", "")
        if rel == "independent" and re.search(r"/(blog|resources|insights|learn)/", url):
            # Company blogs are usually the company's own marketing; the gate cannot know who owns a domain.
            report.warn("self_published_marked_independent", f"{name}: {url} looks like a company's own content")

    # Every fetched source answers a stated question.
    questions = set(plan.questions)
    cited = set()
    for s in plan.sources:
        if s.file not in manifest:
            report.fail("unknown_source", s.file)
        if s.question not in questions:
            report.fail("source_answers_no_question", f"{s.file}: question is not one of the plan's questions")
        cited.add(s.file)
    for name in manifest:
        if name not in cited:
            report.fail("unexplained_document", f"{name} is in the corpus but no source entry says why")

    domains = {e["domain"] for e in manifest.values()}
    types = {d.meta.get("source_type") for d in docs.values()}
    report.metrics = {
        "documents": len(docs),
        "domains": len(domains),
        "source_types": sorted(t for t in types if t),
        "dated": sum(1 for d in docs.values() if "published" in d.meta),
        "questions": len(plan.questions),
    }
    if len(docs) < MIN_RESEARCH_DOCS:
        report.fail("too_few_sources", f"{len(docs)} documents, need {MIN_RESEARCH_DOCS}")
    if len(domains) < MIN_RESEARCH_DOMAINS:
        report.fail("too_few_domains", f"{len(domains)} sites, need {MIN_RESEARCH_DOMAINS}")
    if len(types) < 2:
        report.warn("single_source_type", "every source is the same kind; evidence will have one research method")
    return report


# --------------------------------------------------------------------------------------------
# Entry points

GATES = {
    "research": gate_research,
    "evidence": gate_evidence,
    "strategy_brief": gate_strategy_brief,
    "message_spine": gate_message_spine,
}


def upstream_passed(run_dir: Path, stage: str) -> tuple[bool, str]:
    up = UPSTREAM[stage]
    if up is None:
        return True, ""
    if up == "research" and not (run_dir / "research.json").exists():
        return True, ""
    rpt = run_dir / f"{up}.gate.json"
    if not rpt.exists():
        return False, f"{up} has no gate report; run the {up} stage and its gate first"
    if not json.loads(rpt.read_text(encoding="utf-8")).get("passed"):
        return False, f"{up} gate failed; fix {up} before starting {stage}"
    return True, ""


def run_gate(stage: str, run_dir: Path, repo_root: Path) -> GateReport:
    ok, why = upstream_passed(run_dir, stage)
    if not ok:
        report = GateReport(stage)
        report.fail("upstream_not_passed", why)
    else:
        report = GATES[stage](run_dir, repo_root)
    (run_dir / f"{stage}.gate.json").write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return report
