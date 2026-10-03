---
name: kaizen-research
description: Kaizen stage 0 (optional). Research a market on the web and build the run's corpus from fetched pages, saved verbatim by code. Use when the kaizen pipeline is given a market or product to research instead of an existing corpus.
---

# Stage 0: research

Build the corpus the rest of the pipeline reasons from. You decide what to look for and which pages
to keep. Code fetches each page and saves its text verbatim. **You never write corpus files**: the
hook blocks it, and the gate rejects any document the fetcher did not write or that changed after
it was fetched. Your own synthesis does not belong in the corpus. The evidence and strategy stages
do the synthesis, against the gates.

## 1. Questions

From the brief (the product, the market, the decision to be made), write 3 to 6 research questions
a product marketer needs answered. Cover, where relevant:

- What problem buyers have and what it costs them
- Who buys, who uses, and what triggers a purchase
- What buyers do instead today, including the status quo (spreadsheets, manual work, hiring)
- How the named alternatives position themselves and where buyers say they fall short
- What proof buyers ask for
- What is changing in the market

## 2. Search and choose

Search with WebSearch. For each question, prefer in this order:

1. **Independent evidence of behavior or measurement:** studies with a stated method, surveys with
   a stated sample, regulator or standards-body publications, reported case histories.
2. **Practitioner voices:** forums, community threads, practitioner write-ups.
3. **Trade and news coverage** that reports facts, not vendor announcements rewritten.
4. **Vendor and competitor pages,** for what those vendors claim, never as proof of anything else.

Spread across sites. A press article that rewrites a vendor release adds nothing: the evidence gate
will count the two as one origin.

## 3. Fetch

Fetch each page you keep with:

    python -m kaizen fetch <url> --run runs/<run> --source-type <type> --relation <relation>

- `--source-type`: `deep_research_report` (a study or report with a method), `news_web` (press,
  articles, blogs), `community_forum` (forums, threads, Q&A), `vendor_page` (a vendor's own site)
- `--relation`: `independent`, `vendor`, `competitor`, `sponsored` or `first_party`. A vendor's own
  page is `vendor` or `competitor`; sponsored or paid placement is `sponsored`.

The fetcher refuses pages that robots.txt disallows, non-HTML files (PDFs), and pages with too
little readable text (often script-rendered). Pick another source when that happens. It records the
page's own publication date when the page declares one, and leaves the page undated otherwise; do
not supply dates.

## 4. Plan

Write `runs/<run>/research.json` (shape: `python -m kaizen schema research`):

    {
      "stage": "research",
      "questions": ["..."],
      "queries": ["the searches you ran"],
      "sources": [{"file": "01-example-com-....md", "question": "<one of the questions, verbatim>"}]
    }

Every fetched document needs a source entry naming the question it answers.

## What the gate checks

- Every corpus document was written by the fetcher and is unchanged (hash match).
- No document is missing, and none sits in the corpus without a manifest entry.
- Every source declares a type and relation; a `vendor_page` is never `independent`.
- Every document answers one of the plan's questions.
- At least 5 documents from at least 3 sites.
- Warnings: undated pages, a promotional page marked independent, all sources of one type.

Then hand off to `kaizen-evidence` with the corpus at `runs/<run>/corpus`.
