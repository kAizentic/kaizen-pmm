# kaizen-pmm

An agent-run product marketing pipeline. LLM agents do the judgment at each stage (what to research,
what the evidence shows, what to commit to, how to say it), and deterministic code decides whether
each artifact may ship. The
gates run as Claude Code hooks, so they are not instructions the agent can skip: a failing gate sends
its violations back to the agent, and the next stage cannot start until it passes.

```
market brief  -or-  existing corpus
   |
   v
[research]        agent picks questions and pages; code     -> gate: corpus untampered, every page
   |              fetches and saves each page verbatim         explained, enough independent sites
   v
[evidence]        agent extracts typed, quote-backed claims  -> gate: verified, weighed, origins traced
   |
   v
[strategy brief]  agent commits to ICP, wedge, category, GTM -> gate: grounded, corroborated, committed
   |
   v
[message spine]   agent turns strategy into language         -> gate: proven, anchored, substantiated
```

## Why it is built this way

Language
models are good at the judgment this work needs, such as what counts as a buyer's problem in a
market they have never seen. They are unreliable at holding themselves to evidence. So the agent
writes and the code holds the line.

Each stage's craft was researched against published practice (Porter,
Martin, Rumelt, Moore, Dunford, Patton, Nielsen, the FTC's substantiation standard), and whatever
could be checked mechanically became a gate. [ADR 0003](docs/adr/0003-craft-rules-from-published-practice.md)
maps every gate to its source.

| Stage | The agent decides | The gate enforces |
|---|---|---|
| Research | The questions, the searches, which pages to keep, each source's type and relation | Code fetches and saves every page; the agent cannot write the corpus. Every document matches its fetch hash and answers a stated question. A vendor's own page is never independent. Five or more documents from three or more sites. |
| Evidence | Which claims matter, and what kind of evidence each is | The quote is verbatim in the source. Every number in the claim is in the quote. "I would" and "we always" cannot pass as behavior. Vendor and sponsored sources yield only vendor claims. Documents that rewrite each other count as one origin. |
| Strategy brief | ICP, problem, wedge, category, GTM, what to rule out | Problem and differentiation rest on behavioral or market evidence from two or more independent origins. Differentiation names a real alternative from the evidence. The status quo is considered. Every exclusion has a reason and evidence. Assumptions name what would falsify them. No hedges, one target. |
| Message spine | The narrative, pillars and persona messages | One to four distinct pillars, each with cited proof. Every persona has proof and none is an excluded ICP. "Proven", "40%", "3x" need behavioral or market evidence. Every proof requirement in the strategy has a proof point. Anchored to the strategy's category, wedge and ICP. No superlatives. |

## Run it

Requires Python 3.11+ and [Claude Code](https://claude.com/claude-code).

```bash
pip install -e ".[dev]"
pytest                                   # gate behavior and contracts
claude                                   # then: "run kaizen on examples/ap-automation/corpus"
                                         #   or: "research <market> with kaizen and build a strategy"
```

The pipeline skills live in `.claude/skills/` and the hooks in `.claude/settings.json`, so opening
the repo in Claude Code is the whole setup. The gates also run on their own:

```bash
python -m kaizen fetch <url> --run runs/<run> --source-type news_web --relation independent
python -m kaizen schema strategy_brief           # the contract an agent must satisfy
python -m kaizen gate evidence runs/<run>        # run one gate
python -m kaizen status runs/<run>               # every stage's result, with warnings
```

## Layout

```
kaizen/               gates, contracts, provenance scoring, CLI (no model calls anywhere)
  gate.py             stage gates and the run layout
  fetch.py            the research fetcher: robots.txt, HTML to text, manifest with hashes
  *_contract.py       stage contracts (Pydantic); later stages are contracted, not yet built
.claude/skills/       one skill per stage, plus the `kaizen` orchestrator
.claude/hooks/        hook shim: runs the gate on every artifact write
examples/             synthetic corpus and the committed sample run
docs/adr/             design decisions and the sources behind each gate
```

Contracts for later stages (asset plan, collateral, sales enablement, channel plan, digital
experience, performance review) are in the package; their agent stages are not built yet.

## History

v1 was a deterministic engine: rules wrote every artifact. It was built against a single market and
could not leave it. v2 keeps v1's contracts and provenance scoring, replaces its generation layer
with agents, and replaces its scoring-based admission with gates grounded in published practice.
See [ADR 0001](docs/adr/0001-agents-write-code-gates.md).

## License

Source-available for reading, study and evaluation. See [LICENSE](LICENSE).
