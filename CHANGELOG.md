# Changelog

## 2026-10-01 `root..4a78476`

- Added: a three-stage pipeline (evidence, strategy brief, message spine) where Claude Code skills write each artifact and deterministic gates, run as hooks, decide whether it may ship.
- Added: gate rules derived from published positioning and research practice, each mapped to its source in docs/adr/0003.
- Added: a synthetic accounts-payable sample corpus and a committed sample run that can be inspected without running anything.
- Added: the test suite (83 tests), covering every gate rule in both directions.
