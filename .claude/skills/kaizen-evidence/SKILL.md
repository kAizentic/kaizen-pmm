---
name: kaizen-evidence
description: Kaizen stage 1. Extract quote-backed, typed claims from a research corpus into runs/<run>/evidence.json. Use as the first stage of the kaizen pipeline.
---

# Stage 1: evidence

Read every document in the corpus and extract the claims a product marketer would build a strategy
on: buyer problems and their cost, who buys and why, which alternatives buyers use and how those
win and lose, what proof buyers ask for, and risks.

## Output

Write `runs/<run>/evidence.json`. Get the exact shape with `python -m kaizen schema evidence`.
Each claim has:

- `id`: `E01`, `E02`, ... in order
- `claim`: one sentence stating what the evidence shows
- `quote`: a span copied **verbatim** from the document, at least 20 characters. The gate searches
  for it in the source. Whitespace and markdown emphasis are ignored; everything else must match.
- `doc`: the file name
- `section`: `market_overview`, `key_problems`, `buyer_segments`, `competitive_landscape`,
  `emerging_signals` or `risks_and_uncertainties`
- `claim_type`: `fact`, `inference`, `recommendation`, `risk`, `objection`, `persona_need` or
  `proof_requirement`
- `evidence_kind`: what the quote actually shows, strongest first:
  - `observed_behavior`: what someone did, observed or recorded
  - `past_episode`: a specific past event the speaker took part in
  - `market_data`: a measured figure from an independent study
  - `stated_preference`: what someone says they want or value
  - `prediction`: what someone says they would do
  - `vendor_claim`: anything from a vendor, competitor or sponsored source
- `alternative` and `alternative_type` (together, or neither): when the claim is about something
  buyers use instead, name it and type it as `vendor`, `status_quo`, `diy`, `outsourced`,
  `in_house_build` or `other`. The status quo (spreadsheets, email, doing nothing, hiring someone)
  is an alternative; tag it.

## How to judge kind

Watch what people did, not what they say they will do. "We always", "I would", "we'll never" are
generic or hypothetical talk, whatever the speaker's confidence: tag them `stated_preference` or
`prediction`. Keep the participant's words separate from the interviewer's or author's
interpretation, and quote the participant. A vendor's page is good evidence of what that vendor
claims and weak evidence of anything else.

## What the gate checks

- The quote is in the source.
- Every number in `claim` appears in `quote`.
- A quote containing would, will, might, always, usually, never or "if we" cannot be tagged
  `observed_behavior` or `past_episode`.
- Claims from a vendor, competitor or sponsored source (declared in the document's
  `author_relation`, or detected from promotional wording) must be tagged `vendor_claim`.
- At least 6 admitted claims that are not vendor claims.
- No score fields or any field not in the schema.

The gate also groups documents into independent origins (two documents sharing long passages are
one origin) and records each source's research method. Later stages are checked against those.

Extract from every document, including ones you expect to be weak. Aim for 25 to 40 claims and
prefer claims with a number, a named alternative, or a decision a buyer made.
