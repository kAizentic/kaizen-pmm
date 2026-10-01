---
name: kaizen
description: Run the Kaizen product marketing pipeline on a research corpus - evidence, then strategy brief, then message spine - with a deterministic gate after every stage. Use when the user says "run kaizen", "run the pipeline on <corpus>", or asks to turn market research into a strategy brief and messaging.
---

# Kaizen pipeline

You write each artifact. Code decides whether it passes. A hook runs the stage's gate every time
you write an artifact, and blocks you from starting a stage until the stage before it has passed.

Commands below use `python`; on systems where that name is missing use `python3` or `py`.

## Run it

1. Pick a run directory: `runs/<run-name>/` (one per run, never reused).
2. Run the stages in order, using each stage's skill:
   1. `kaizen-evidence` writes `evidence.json`
   2. `kaizen-strategy-brief` writes `strategy_brief.json`
   3. `kaizen-message-spine` writes `message_spine.json`
3. After each write the hook prints `gate passed` or a list of violations. On a failure, fix the
   artifact and write it again. Do not move on with a failing gate, and do not edit any
   `*.gate.json` or `evidence.scored.json` file: those are written by the gate, not by you.
4. Finish with `python -m kaizen status runs/<run-name>` and report each stage's result.

## Rules that hold across stages

- Only the corpus is evidence. Do not add facts from your own knowledge.
- Every load-bearing field cites evidence ids from `evidence.scored.json`, and only admitted ones.
- If the evidence does not support a decision, say so in the artifact (for example in
  `decision_rationale` or `strategic_risks`) rather than inventing support.
