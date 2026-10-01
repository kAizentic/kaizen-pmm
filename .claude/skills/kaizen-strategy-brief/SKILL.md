---
name: kaizen-strategy-brief
description: Kaizen stage 2. Commit to a product marketing strategy from admitted evidence and write runs/<run>/strategy_brief.json. Use after the evidence gate has passed.
---

# Stage 2: strategy brief

The strategy brief makes decisions. It commits to one target customer, one problem frame, one wedge,
one category frame and one GTM motion, names what it is choosing **not** to do and why, and writes
down what must be true for it to work. "The essence of strategy is choosing what not to do"
(Porter, 1996).

## Input

`runs/<run>/evidence.scored.json`. Cite only claims with `"admitted": true`.

## Work in this order

1. **Competitive alternatives first:** what would buyers do if this product did not exist? Include
   the status quo (spreadsheets, email, hiring someone, doing nothing); it is usually the biggest
   competitor.
2. **What the product does that those alternatives cannot**, then the value that creates.
3. **Who cares most about that value:** the target customer, defined by the circumstance that makes
   them care, not by size and industry alone. Pick one. You do not have to pick the optimal target,
   only one you can win.
4. **Category last:** choose a frame that makes the value obvious, and a style: `existing`,
   `subsegment` (a niche of an existing category), `reframe`, or `new`. Prefer a niche; category
   creation is the hardest to execute.
5. **The obstacle:** what stands in the way. A strategy that does not name the obstacle is a goal.
6. **Assumptions:** what must be true, each with the observation that would falsify it.

Test urgency honestly: if buyers can live with the problem for another year, they will.

## Output

Write `runs/<run>/strategy_brief.json`:

    {
      "stage": "strategy_brief",
      "payload": { ...the strategy brief contract... },
      "citations": { "<payload field>": ["E03", "E11"], ... }
    }

Get the payload schema and section intent with `python -m kaizen schema strategy_brief`.
`excluded_icps` and `rejected_gtm_motions` are lists of `{item, reason, evidence}`; `assumptions`
is a list of `{assumption, what_would_falsify}`.

## What the gate checks

- The payload validates against the contract (v2).
- `strategic_recommendation`, `recommended_icp`, `problem_frame`, `wedge`,
  `differentiation_claim`, `proof_requirements` and `preferred_gtm_motion` each cite admitted
  evidence, and none rests only on `recommendation`-type evidence.
- `problem_frame` and `differentiation_claim` each cite at least one `observed_behavior`,
  `past_episode` or `market_data` claim, from at least **two independent origins**. Vendor claims
  do not count. `problem_frame`, being a claim about how common the problem is, also needs at least
  two research methods (source types).
- `differentiation_claim` names an alternative that appears in admitted competitive evidence, and
  cites competitive evidence.
- The brief cites at least one status-quo or do-it-yourself alternative somewhere.
- Every exclusion has a reason and cites admitted evidence showing it was a real option.
- No hedges ("could", "might", "consider", "explore", "options include") in the recommendation, the
  ICP, the wedge or the GTM motion, and the ICP names one segment ("and/or", "as well as" fail).
- No research leakage, generic language ("leverage", "optimize") or superlatives.

Warnings (not blocking): next moves that do not connect to a blocker, risk or proof requirement;
category style `new`.

If the evidence cannot support a field to that standard, narrow the claim until it can and record
the gap in `strategic_risks` or `assumptions`.
