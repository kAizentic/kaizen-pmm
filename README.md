# kaizen-pmm

An agent-run product marketing pipeline. LLM agents write each artifact (the evidence base, the
strategy brief, the message spine), and deterministic code decides whether each one may ship. The
gates run as Claude Code hooks, so they are not instructions the agent can skip: a failing gate sends
its violations back to the agent, and the next stage cannot start until it passes.

```
research corpus
   |
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

A rule written into a prompt is a request. A rule enforced by a hook is a constraint. Language
models are good at the judgment this work needs, such as what counts as a buyer's problem in a
market they have never seen. They are unreliable at holding themselves to evidence. So the agent
writes and the code holds the line.

The rules are not invented. Each stage's craft was researched against published practice (Porter,
Martin, Rumelt, Moore, Dunford, Patton, Nielsen, the FTC's substantiation standard), and whatever
could be checked mechanically became a gate. [ADR 0003](docs/adr/0003-craft-rules-from-published-practice.md)
maps every gate to its source.

| Stage | The agent decides | The gate enforces |
|---|---|---|
| Evidence | Which claims matter, and what kind of evidence each is | The quote is verbatim in the source. Every number in the claim is in the quote. "I would" and "we always" cannot pass as behavior. Vendor and sponsored sources yield only vendor claims. Documents that rewrite each other count as one origin. |
| Strategy brief | ICP, problem, wedge, category, GTM, what to rule out | Problem and differentiation rest on behavioral or market evidence from two or more independent origins. Differentiation names a real alternative from the evidence. The status quo is considered. Every exclusion has a reason and evidence. Assumptions name what would falsify them. No hedges, one target. |
| Message spine | The narrative, pillars and persona messages | One to four distinct pillars, each with cited proof. Every persona has proof and none is an excluded ICP. "Proven", "40%", "3x" need behavioral or market evidence. Every proof requirement in the strategy has a proof point. Anchored to the strategy's category, wedge and ICP. No superlatives. |

Two rules were built, measured and replaced on the way.
[ADR 0002](docs/adr/0002-evidence-admission.md) dropped an inherited six-dimension signal score that
scored a sponsored vendor post the same as an analyst brief. ADR 0003 replaced a word-overlap drift
check that rewarded copying the strategy's jargon.

## The sample run

[`examples/ap-automation/`](examples/ap-automation/) runs the pipeline on a synthetic corpus about
a fictional accounts-payable product: Northwind AP, competing with Contoso and Fabrikam. The corpus
holds eight documents: an analyst brief, three customer interviews, win/loss notes, a trade article,
a practitioner forum thread, and one sponsored vendor post planted to test how vendor sources are
handled.

One headless Claude Code session ran all three stages in about three and a half minutes:

| Stage | Result |
|---|---|
| Evidence | 51 claims, all verified. 27 behavioral (observed or past episode), 10 market data, 12 stated preferences or predictions, 2 vendor claims from the sponsored post. 8 independent origins, 3 research methods. |
| Strategy brief | **Failed once, then passed.** The first draft differentiated "unlike outsourced AP"; the gate requires an alternative named in the evidence, and the agent rewrote it as "unlike Fabrikam Payables Services". Problem frame: 4 origins, 2 methods. Differentiation: 4 origins. |
| Message spine | Passed. Four pillars, each with cited proof; anchors to the strategy's category, wedge and ICP all present. |

Read [`run/strategy_brief.json`](examples/ap-automation/run/strategy_brief.json) for the output. It
excludes three ICPs and three GTM motions with reasons, and writes three falsifiable assumptions,
for example that Contoso keeps single-approver routing, falsified if "Contoso ships multi-level
routing with escalation and non-ERP approvals, and win rate against it drops".

## Run it

Requires Python 3.11+ and [Claude Code](https://claude.com/claude-code).

```bash
pip install -e ".[dev]"
pytest                                   # gate behavior and contracts
claude                                   # then: "run kaizen on examples/ap-automation/corpus"
```

The pipeline skills live in `.claude/skills/` and the hooks in `.claude/settings.json`, so opening
the repo in Claude Code is the whole setup. The gates also run on their own:

```bash
python -m kaizen schema strategy_brief           # the contract an agent must satisfy
python -m kaizen gate evidence runs/<run>        # run one gate
python -m kaizen status runs/<run>               # every stage's result, with warnings
```

## What the gates do not catch

- **Plausible but unsupported detail.** In the sample run a pillar credits Northwind with approval
  *delegation*. The evidence shows buyers lack delegation today, not that the product provides it.
  Citations prove a field draws on admitted evidence, not that every phrase in it does.
- **Whether the copy is on strategy in meaning.** The spine is anchored to the strategy's terms; a
  judgment of whether it is truly on strategy needs a review stage, which a deterministic gate
  cannot be.
- **Numbers written as words.** The number check compares digits. In one run the agent satisfied it
  by writing "twelve" in the claim.
- **Quality.** A gate can say an artifact is grounded, corroborated and consistent, not that it is
  good. There is no output-quality evaluation yet.

## Layout

```
kaizen/               gates, contracts, provenance scoring, CLI (no model calls anywhere)
  gate.py             stage gates and the run layout
  *_contract.py       stage contracts (Pydantic); later stages are contracted, not yet built
.claude/skills/       one skill per stage, plus the `kaizen` orchestrator
.claude/hooks/        hook shim: runs the gate on every artifact write
examples/             synthetic corpus and the committed sample run
docs/adr/             design decisions and the sources behind each gate
```

Contracts for later stages (asset plan, collateral, sales enablement, channel plan, digital
experience, performance review) are in the package; their agent stages are not built yet. A research
stage that fetches sources into the corpus is planned, under the same rule as everything else: it
saves the pages it fetched verbatim, never its own summary.

## History

v1 was a deterministic engine: rules wrote every artifact. It was built against a single market and
could not leave it. v2 keeps v1's contracts and provenance scoring, replaces its generation layer
with agents, and replaces its scoring-based admission with gates grounded in published practice.
See [ADR 0001](docs/adr/0001-agents-write-code-gates.md).

## License

Source-available for reading, study and evaluation. See [LICENSE](LICENSE).
