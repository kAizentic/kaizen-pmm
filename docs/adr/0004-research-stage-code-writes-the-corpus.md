# 0004: The research stage chooses sources; code writes the corpus

**Status:** accepted, 2026-10

## Context

Every downstream gate checks artifacts against the corpus: quotes must be verbatim, origins are
counted per document, vendor sources are restricted. Those checks are only as good as the corpus is
honest. A research stage that let the agent write corpus documents would undo them. An agent could
save its own synthesis as a "report", and the evidence gate would then verify quotes against text
the agent wrote. The provenance layer would make this worse, because it gives
`deep_research_report` the highest authority of any source type.

## Decision

Split the stage the same way as the rest of the pipeline: the agent judges, code does the part that
must be trustworthy.

- **The agent** writes the research questions, runs the searches, chooses which pages to keep and
  declares each one's source type and author relation.
- **`python -m kaizen fetch`** downloads each page, extracts its readable text, takes the
  publication date from the page's own metadata (or leaves it undated), writes the corpus document
  and records a SHA-256 of its body in `corpus/_manifest.json`.
- **The hook** blocks any agent write or edit inside a run's `corpus/` folder.
- **The research gate** checks that every document has a manifest entry and an unchanged hash, that
  no manifest entry is missing its file, that every source declares its type and relation (and a
  vendor's own page is never `independent`), that every document answers one of the plan's
  questions, and that the corpus spans at least five documents from three sites.
- **Evidence waits for research** when a run has a research plan, and runs as before on a supplied
  corpus.

This is a guarantee by construction rather than by detection. The agent never writes page text, so
there is nothing to catch. The hash check covers the remaining paths: a hand edit, a stray file, a
tool other than Write or Edit.

## Consequences

- robots.txt is read the way RFC 9309 specifies: requested with the fetcher's own user agent; a 2xx
  is obeyed, a 4xx means no rules apply, a 5xx or no answer means do not fetch. Python's
  `robotparser.read()` was used first and was wrong in practice. It requests robots.txt with
  Python's default user agent, which many sites answer with 403, and then treats 403 as
  "disallow everything". The first live run lost Wikipedia, cfo.com and ten other pages to that
  alone.
- The fetcher is standard-library only and reads HTML. It refuses PDFs, pages that robots.txt
  disallows, and pages with too little readable text (usually script-rendered). Those limits are
  visible to the agent, which picks another source.
- Text extraction is simple: it keeps paragraphs, list items, headings, quotes and table cells, and
  drops scripts, navigation, headers, footers and forms. Some sites will lose content or keep
  boilerplate. Because the agent never touches the text, this is a fidelity limit and not a
  trust problem.
- Author relation is still declared by the agent, and the gate cannot know who owns a domain. A
  vendor page labelled independent is caught when it is typed `vendor_page`, or when its text is
  promotional (the evidence gate then treats it as sponsored). The first live run showed the
  remaining gap: a consultancy's marketing blog and a referral marketplace, both labelled
  independent and neither promotional enough to trip the detector. Pages under `/blog/`,
  `/resources/`, `/insights/` or `/learn/` that are marked independent now raise a warning for the
  reviewer. It does not block, because independent publications use those paths too.
- The committed sample run stays on the synthetic corpus, because a fictional product cannot be
  researched on the live web.
