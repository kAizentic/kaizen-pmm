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
| Research | The questions, the searches, which pages to keep, each source's type and relation | Code fetches and saves every page; the agent cannot write the corpus. Every document matches its fetch hash and answers a stated question. A vendor's own page is never independent. Five or more documents from three or more sites. |
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

## Research on the live web

The committed sample uses a synthetic corpus because its product is fictional. The research stage
was checked live instead, on the real mid-market accounts-payable market (output not committed):

- 5 questions, 16 searches, 11 documents from 8 sites, in about five minutes. Five pages were
  refused by the sites themselves (HTTP 403 or 406 to automated clients); the agent chose others.
- The evidence gate admitted 44 claims. 21 were vendor claims, and only 12 were behavioral or
  market data; the rest were stated preferences. That is what the open web offers for a software
  category, and the gates make it visible: vendor claims cannot carry the problem frame or the
  differentiation, so a strategy built on this corpus has to work with 12 strong claims or go and
  find more.
- Three practitioner threads were five to eight years old and were flagged stale.
- An earlier live run labelled a consultancy's marketing blog and a referral marketplace as
  independent. That led to a reviewer warning for company-owned content marked independent; see
  [ADR 0004](docs/adr/0004-research-stage-code-writes-the-corpus.md). The same run exposed a
  fetcher bug: Python's robots.txt reader asks with its default user agent, many sites answer that
  with 403, and the reader then treats the whole site as off limits. Wikipedia, cfo.com and others
  were refused for that reason alone. The fetcher now follows RFC 9309 and asks as itself.

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

## What the gates do not catch

- **Plausible but unsupported detail.** In the sample run a pillar credits Northwind with approval
  *delegation*. The evidence shows buyers lack delegation today, not that the product provides it.
  Citations prove a field draws on admitted evidence, not that every phrase in it does.
- **Whether the copy is on strategy in meaning.** The spine is anchored to the strategy's terms; a
  judgment of whether it is truly on strategy needs a review stage, which a deterministic gate
  cannot be.
- **Numbers written as words.** The number check compares digits. In one run the agent satisfied it
  by writing "twelve" in the claim.
- **Who owns a website.** The research agent declares whether a source is independent. A
  company's blog marked independent raises a warning, not a block.
- **Pages the fetcher cannot read.** PDFs and script-rendered pages are refused rather than
  half-read, which narrows what research can reach.
- **Quality.** A gate can say an artifact is grounded, corroborated and consistent, not that it is
  good. There is no output-quality evaluation yet.

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
