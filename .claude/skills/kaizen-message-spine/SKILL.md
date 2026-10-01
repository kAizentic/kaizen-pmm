---
name: kaizen-message-spine
description: Kaizen stage 3. Turn the approved strategy brief into a message spine and write runs/<run>/message_spine.json. Use after the strategy brief gate has passed.
---

# Stage 3: message spine

The message spine turns the strategy into language buyers will hear. It does not reopen any
decision: the positioning sets the criteria for accepting or rejecting copy, and copy that is not on
strategy is not acceptable however good it sounds.

## Input

- `runs/<run>/strategy_brief.json` (the source of truth for every decision)
- `runs/<run>/evidence.scored.json` (admitted claims only)

## How to write it

- **Narrative:** name a shift in the world that creates stakes and urgency (a change, not a problem
  statement), then the future state buyers can reach (not the product), then the evidence that it
  works, ideally a success story from someone like the buyer.
- **Pillars:** one to four, distinct, each about differentiated value. Parity points belong in the
  objection map, not in pillars.
- **Personas:** the strategy's target customer comes first. Each row restates one claim in that
  role's own terms, with the proof that role trusts.
- **Buyer language:** translate internal labels and strategy jargon into the words buyers use.
- **Telling details over adjectives:** a specific figure or episode beats "fast", "powerful",
  "seamless".

## Output

Write `runs/<run>/message_spine.json`:

    {
      "stage": "message_spine",
      "payload": { ...the message spine contract... },
      "citations": {
        "value_pillars.0": [...], "value_pillars.1": [...],
        "persona_message_hierarchy.0": [...],
        "proof_points": [...], "objection_map": [...]
      }
    }

Cite each pillar and each persona row by index. Get the payload schema with
`python -m kaizen schema message_spine`.

## What the gate checks

- The payload validates against the contract.
- One to four pillars, no two near-duplicates, each cited with admitted evidence.
- Every persona row has `supporting_proof` and an indexed citation; no persona is one of the
  strategy's excluded ICPs.
- Wording that claims support ("proven", "studies show", "%", "3x", "times faster") cites an
  `observed_behavior`, `past_episode` or `market_data` claim.
- Every strategy `proof_requirements` item maps to a proof point.
- The call to action does not run a rejected GTM motion.
- Anchors to the strategy: the category statement carries the head noun of the strategy's
  `category_frame`, at least one pillar carries two key terms of the `wedge`, and the first persona
  is the `recommended_icp`.
- The spine does not use its own `forbidden_language`, and has no leakage, generic language or
  superlatives ("best-in-class", "seamless", "all-in-one").
