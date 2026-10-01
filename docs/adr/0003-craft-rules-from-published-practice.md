# 0003: Gate rules derived from published practice

**Status:** accepted, 2026-10

## Context

The first gates checked structure: contracts, citations, a two-source rule, a word-overlap drift
check. Before publishing, each stage's craft was researched against published practice to find what
an expert would check that the gates did not. Three findings overturned rules already built:

- A verbatim quote proves someone said it, not that it is strong evidence.
- Counting a source as type plus platform made twelve independent interviews one source, and a press
  rewrite of a vendor release two.
- A word-overlap floor between spine and strategy rewards copying the strategy's jargon, where
  practice asks for buyer language.

## Decision

Rules that can be checked mechanically became gates. Judgment that cannot went into the skills.
Each gate below cites the practice it encodes.

### Evidence

| Rule | Basis |
|---|---|
| Every claim carries an `evidence_kind`; problem and differentiation need behavioral or market evidence | "Watch what people actually do. Do not believe what people say they do." (Nielsen, *First Rule of Usability? Don't Listen to Users*, nngroup.com) |
| A quote with would / will / always / usually / never cannot be tagged as behavior | Generic and hypothetical talk (Fitzpatrick, *The Mom Test*, ch. 2) |
| Every number in a claim appears in its quote | Separate what was found from interpretation (atomic research practice) |
| Vendor, competitor and sponsored sources yield only `vendor_claim` | Industry sponsorship produces bias "that cannot be explained by standard 'Risk of bias' assessments" (Lundh et al., Cochrane Review, 2017) |
| Corroboration counts independent origins; documents sharing long passages are one origin | Triangulation of sources within and across methods (Patton, 1999, *Health Services Research* 34(5)) |
| Prevalence claims need two research methods; best-fit fields do not | Findings "must be carefully limited… to those situations and cases in the sample" (Patton, 1999) |

### Strategy brief

| Rule | Basis |
|---|---|
| Differentiation names an alternative found in the evidence | "Unlike (the product alternative)" (Moore, *Crossing the Chasm*, ch. 6); positioning starts from competitive alternatives (Dunford) |
| The status quo is considered | In B2B "our biggest competitor is actually Excel" (Dunford) |
| Exclusions carry a reason and evidence | "The essence of strategy is choosing what not to do" (Porter, *What Is Strategy?*, HBR 1996); planning should be explicit about "what the organisation chooses not to do and why" (Martin, 2014) |
| Assumptions with what would falsify them | "What do you need to believe… It is critical to write down the answers" (Martin, 2014) |
| No hedges in commitment fields | Fluff as "a restatement of the obvious… buzzwords that masquerade as expertise" (Rumelt, McKinsey Quarterly, 2011) |
| One target customer | "For (target customers—beachhead segment only)" (Moore, ch. 6) |
| Load-bearing fields rest on facts, not only on someone else's recommendation | A strategy is a choice, not a restatement of advice (Rumelt, 2011) |
| Category style is declared; `new` warns | Category creation is "by far the most difficult to execute on" (Dunford) |

### Message spine

| Rule | Basis |
|---|---|
| Anchor checks replace word overlap | Positioning "sets the criteria for accepting or rejecting ad copy" (Moore); use buyer language, avoid internal labels (Wynter) |
| One to four distinct pillars, each with cited proof | "If a pillar lacks proof, either strengthen real-world evidence or drop the claim" (message-house practice, Umbrex) |
| Support wording needs behavioral or market evidence | Advertisers need "at least the advertised level of substantiation" (FTC Policy Statement on Advertising Substantiation) |
| Every strategy proof requirement maps to a proof point | Claims need "sufficient evidence as to make any such disputation unreasonable" (Moore, ch. 6) |
| No superlatives or sameness phrases | Mark "claims any competitor could make" (Wynter) |

## What was not adopted

- **Counting value themes against proof requirements:** themes in free text cannot be counted
  reliably.
- **Recency windows by source type:** uncalibrated. Undated and stale sources warn instead.
- **Interviewer-echo detection:** needs speaker-labelled transcripts.
- **An on-strategy judgment inside a gate:** a model call in a gate would break the rule that gates
  are deterministic. It belongs in a separate review stage.
- **GTM thresholds by deal size:** published sources disagree by 5 to 25 times.

## Evidence quality of the research itself

Principles rest on Porter, Martin, Rumelt, Moore, Patton, Nielsen and the FTC. Practitioner material
on ICPs, GTM motions and win/loss came mostly from vendors of those services and is treated as
directional. Quotes seen only in secondary sources were left out of this document.
