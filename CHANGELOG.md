# Changelog

## 2026-10-03 `bb1fc07..86bbba0`

- Added: an optional research stage. The agent chooses questions, searches and pages; `python -m kaizen fetch` saves each page's text verbatim with a hash, and agents cannot write to the corpus.
- Added: a research gate that checks every page is unchanged since it was fetched, answers a stated question, and that the corpus spans enough sites; company-owned content marked independent raises a warning.
- Changed: the evidence stage waits for the research gate when a run includes research.
- Added: tests for the fetcher and research gate against a local web server (98 tests in total).

## 2026-10-01 `root..4a78476`

- Added: a three-stage pipeline (evidence, strategy brief, message spine) where Claude Code skills write each artifact and deterministic gates, run as hooks, decide whether it may ship.
- Added: gate rules derived from published positioning and research practice, each mapped to its source in docs/adr/0003.
- Added: a synthetic accounts-payable sample corpus and a committed sample run that can be inspected without running anything.
- Added: the test suite (83 tests), covering every gate rule in both directions.
