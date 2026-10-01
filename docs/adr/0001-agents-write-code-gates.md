# 0001: Agents write the artifacts; deterministic code gates them

**Status:** accepted, 2026-10

## Context

Kaizen v1 was a deterministic engine. Rules extracted claims, composed positioning lines and wrote
every artifact from keyword matches. It produced a complete artifact chain for the one market it
was developed against, and that was the problem: the vocabulary that decided what counted as a
pain, an advantage or a buying trigger was specific to that market. A measured pass over v1 found
the generation layer carried several hundred market-specific terms, while the contract, scoring and
consistency modules carried none.

## Decision

Split the system along that line.

- **Generation goes to agents.** Each stage is a Claude Code skill that reads the stage's contract
  (`python -m kaizen schema <stage>`) and writes a JSON artifact. Deciding what counts as a buyer
  problem in a given market is exactly the judgment a language model brings to any market without a
  keyword list.
- **Judgment about whether an artifact may ship stays in code.** The v1 contracts, provenance
  scoring and leakage guards were kept unchanged, and new gates were written for evidence
  verification, citation, the two-source rule and spine alignment. A gate runs on every write and a
  failing gate blocks the next stage.
- **Enforcement is a hook, not an instruction.** The skills describe the rules, and
  `.claude/settings.json` makes them binding: a stage cannot be written until the stage before it
  passes, gate output cannot be written by an agent, and a failed gate sends its violations back to
  the agent to fix.

## Consequences

- The system works for any market, because no market vocabulary lives in code.
- Output is no longer reproducible run to run. Tests therefore assert gate behavior, not artifact
  text. Artifact quality needs its own evaluation, which is not built yet.
- A sample run needs a model to produce. The committed sample run (`examples/ap-automation/run/`)
  can be inspected without running anything.
