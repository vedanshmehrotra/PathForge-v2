# Explicit ground-truth maintenance

Normal generation is insert-only. Cached preparation and DB-only analysis do
not regenerate, repair or replace existing rows. Maintenance is a separate,
explicit operation, never an application endpoint or startup task.

## Packages and operations

`scripts/prepare_ground_truth_correction.py` prepares an inactive package from
a problem snapshot, the complete previous ground-truth row and a reason.
It has no database connection, provider call or product approval workflow.

- `REPLACE` (default, including older packages) requires explicit proposed
  approaches. The existing builder validates complete component requirements,
  alternative boundaries and descriptive unsupported mechanisms. Replacements
  remain `llm_proposed`; previous authority is not inherited.
- `RETIRE` must be explicit and must not supply a replacement response. It
  removes active requirements, sets the row status to `unobserved` and retains
  its entire previous artifact. It does not guess a new approach. Both endpoints
  return the existing `409 GROUND_TRUTH_UNAVAILABLE`, without regeneration.

Packages retain source/old/proposed hashes, the raw proposal, correction reason
and caller-supplied generation metadata. Unknown provider/model details remain
null. Integrity checks do not prove authenticity, algorithmic suitability or
exhaustive approach coverage. Ground truth must not be relabeled to improve
detector or evaluation results.

## Preview and application

Keep request, package and verification artifacts outside the checkout. Existing
files are not overwritten by the preparation CLI.

```powershell
python -B scripts/prepare_ground_truth_correction.py --input C:/external/request.json --output C:/external/package.json
python -B scripts/activate_ground_truth_correction.py --package C:/external/package.json
```

Preview is read-only. Only an explicitly authorized `--apply` stages updates
and commits the supplied batch once. Repeated `--package` arguments form one
transaction: any stale source/row, invalid package or failed write rolls back
the whole batch. It locks/checks the exact current source and old artifact,
then updates only the specified `problem_ground_truth` rows. No schema,
problem, user, submission, skill, gap or recommendation updates are performed.

## Revision storage and compatibility

The existing JSONB column holds revision history; no migration is needed.
The first ordinary group carries `correction_revision` with the complete old
row, version, operation, source/package hashes, reason and generation metadata.
Versions increase and later corrections retain the complete earlier history.

Descriptive-only replacements and retirements have no ordinary approach.
Their history uses an explicitly nonmatchable `record_role=revision_archive`
envelope with empty patterns and required concepts. Its `EXPLICIT` marker
prevents existing readers from reviving curated CSV labels through fallback;
it does not declare a solution approach. This envelope is maintenance-only,
not generator output. Existing readiness checks reject it before analysis or
skill persistence. With valid descriptions the result is the existing
`409 COMPARISON_UNSUPPORTED`; retirement without descriptions remains
`409 GROUND_TRUTH_UNAVAILABLE`. Descriptions retain their strict record shape,
and public serialization never exposes the revision archive.

Tests exercise the actual cached resolver and both endpoints, including stale
curated labels, no regeneration, no analysis/persistence, nested history,
rollback and ordinary supported replacements. Runtime generation still
rejects empty or malformed output before storing it.
