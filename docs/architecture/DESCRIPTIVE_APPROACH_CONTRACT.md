# Descriptive approaches and comparison coverage

Local contract version 2. No live data changes, migrations or authority changes.

## Decision

The rated pattern catalogue is not a catalogue of every valid algorithm. Keep
descriptive proposals separate from matchable requirements. A description is
unverified model output, not a correctness or optimality judgment. Exhaustive
output generation, ordinary bracket matching and depth counting are examples;
the implementation contains no problem-ID exceptions or new detector labels.

Generation retains the existing flat pattern union and explicit approaches.
A fully representable approach retains its complete conjunctive requirements.
An incompletely representable approach must use `comparison_support=UNSUPPORTED`,
empty `patterns`, a name, description and coverage limit. Do not retain only the
supported part as if it described the complete approach. Version 1 remains
compatible; empty/malformed responses and invented pattern IDs still fail.

## Storage and loading

- Existing `solution_groups` JSONB supports a tagged `unscored_approach` record;
  this is a description record, never an empty solution group. It carries contract
  version 2, a source-text SHA-256, proposed provenance and no approved authority.
- Existing matchable groups retain their representation. New records are
  validated before writing and before loading; unknown tags, malformed fields
  and attempted authority changes fail closed.
- Resolver separates descriptions before vocabulary refresh, reconciliation,
  matching, Shadow, primary selection, authority and persistence. Descriptions
  never become required patterns or influence eligibility. Existing rows are
  neither regenerated nor rewritten; ordinary repeat visits reuse new records.
- Ordinary generation uses an insert-only conflict policy. If another request
  saved a row after the cache check, its contents and authority are preserved
  and the resolver reloads that row. This prevents overwrites, not duplicate
  provider calls or an exactly-once guarantee.
- No new tables or migration are necessary. The existing explicit correction
  package can describe a proposed revision but remains inactive; revision
  activation/archive and concurrency are separate, unfinished work.

## API and user behavior

| Preparation state | Response and consequences |
| --- | --- |
| Usable matching groups | Existing 200, plus additive `unscored_approaches` when present. |
| Valid descriptions only | 409 `COMPARISON_UNSUPPORTED`, with descriptions and problem identity. Valid descriptive proposals are cached, but comparison is not declared ready. |
| Empty/malformed generation | Existing HTTP 502; no ground-truth write. |
| Old unusable/corrupt stored data | Existing 409 `GROUND_TRUTH_UNAVAILABLE`; unchanged and never regenerated. |
| Cache missing during analysis | Existing 409 `PREPARATION_REQUIRED`; no preparation. |

`/analyze` remains DB-only. With description-only context it rejects before
analysis/submission persistence. The UI offers **Inspect code only**: a deliberate
action clears problem selection, retains code and explains the missing comparison.
It does not auto-submit. Code-only analysis may save practice, without Elo/gaps.
Mixed comparisons show supported requirements and descriptive alternatives
separately; unused descriptions are not missing skills. Existing skill gates,
canonical authority, ONE_OF, Shadow policies and feature defaults do not change.

## Limits and release requirements

This solves representation and honest feedback, not the truth of model proposals,
exhaustiveness of families, detector coverage or functional solution correctness.
No external model or database was needed for local implementation. Validate live
generation separately before claiming provider compliance. Deploy backend readers
and writers together before allowing new records; historical binaries and direct
JSONB consumers may not understand tagged records. Do not roll back writers/readers
blindly after new records exist. Older frontend payloads remain compatible.

Acceptance covers descriptive-only, mixed and supported approaches; repeated
cache hits; malformed output/stored records; actual engines and persistence;
explicit code-only choice; no skill consequences; stale preparation responses.
