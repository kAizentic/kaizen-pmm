# 0002: Admit evidence by verification and provenance, not by signal score

**Status:** accepted, 2026-10

## Context

v1 ships a six-dimension signal score (problem clarity, buyer salience, commercial impact,
differentiation opening, evidence strength, actionability) with a coherence chain, provenance and
corroboration multipliers and P0 to P3 tiers. The obvious design was to admit evidence at P0 to P2.

It was measured before being adopted. Eight real, quote-backed claims from the sample corpus all
scored P3, with composites between 0.04 and 0.12 against a P2 floor of 0.38. A claim from a
sponsored vendor post scored 0.06, inside the same range as the analyst brief and the interviews.
Corroboration found no peers for any claim. The score was tuned on long, keyword-dense community
posts and does not separate good from bad evidence when the input is a single extracted claim.

Lowering the thresholds until claims pass would be tuning without labels: it would make the gate
pass without making it discriminate.

The score also accepts `score_hints`, and four or more hints replace the heuristics entirely. An
agent allowed to write hints would be scoring its own evidence.

## Decision

Evidence is admitted when:

1. its quote is found verbatim in the cited source document, and
2. the source is not promotional: provenance is scored per document, on the full text, and three or
   more promotional markers exclude every claim from that document.

The agent cannot supply scores: the evidence schema forbids any field it does not define.

Corroboration moves to where it matters. The strategy brief's `problem_frame` and
`differentiation_claim` must cite admitted evidence from at least two distinct sources, where a
source is a type plus a platform, so three interviews from one programme count once.

`scoring_service` stays in the package with its tests, out of the gate path.

## Consequences

- Measured on the sample corpus: the fabricated-quote probe is rejected, the sponsored post is the
  only source excluded (promotional penalty 0.344; every other source 0.000), and real claims are
  admitted.
- Admission no longer ranks evidence. If ranking is needed later, it needs labeled examples first.
