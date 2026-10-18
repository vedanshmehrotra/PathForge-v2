# Ground-truth correction boundary

## Implemented locally

`scripts/prepare_ground_truth_correction.py` prepares an **inactive** JSON
package from a supplied problem snapshot, previous ground-truth snapshot and
saved proposed model response. It has no database connection, LLM call, API
endpoint, activation command or automatic user-review workflow. Ordinary
analysis/preparation behavior is unchanged.

The package retains the entire previous JSON artifact (including malformed
historical fields), its fingerprint, the problem source fingerprint, raw
proposal, normalized proposed groups, correction reason and preparation time.
Unknown model, prompt version and generation time remain null; supplied
generation metadata is explicitly unverified. These hashes provide integrity
checks, not authenticity or algorithmic proof. Native JSON and JSON stored as
text retain their supplied representation; do not silently convert old exports.

The shared builder normalizes and constructs the replacement. Explicit
approaches are required for corrections; complementary components and declared
alternatives retain their existing semantics. Malformed/empty/unsupported
output is rejected. Missing canonical Shadow coverage remains a limitation,
not proof of invalid ground truth. Every replacement stays `llm_proposed`;
previous approval fields and claims inside model output cannot grant authority.

This validates structure/vocabulary only. It cannot decide that a monotonic
stack expectation is suitable for ordinary bracket matching, prove a complete
set of solution families, or represent a currently unsupported depth approach.
No example in this document is a proposed correction to a real cached row.

## Local usage

Keep request exports and output outside the repository. Input shape:

```json
{
  "problem": {"id": 209, "title": "Synthetic fixture", "description": "Frozen problem description"},
  "previous_ground_truth": {"problem_id": 209, "patterns": "[]", "solution_groups": []},
  "proposed_response": {
    "patterns": ["prefix_sum", "hash_map_lookup"],
    "approaches": [{"name": "Combined synthetic approach", "patterns": ["prefix_sum", "hash_map_lookup"]}]
  },
  "correction_reason": "Synthetic validation example only",
  "generation": {"provider": null, "model": null, "prompt_version": null, "generated_at": null, "finish_reason": null}
}
```

```powershell
python -B scripts/prepare_ground_truth_correction.py --input C:/external/request.json --output C:/external/candidate.json
```

The destination must be outside the checkout, its parent must exist, and an
existing file is never overwritten. The package state is `PREPARED_NOT_ACTIVE`.
Running this does not correct the website or claim a deployed data change.

## Activation: separate reviewed change

Repository schema inspection found only the current `problem_ground_truth`
table and no revision archive. `_store_ground_truth` still has its existing
upsert; it is **not** a correction interface and must not be invoked to replace
cached data. Resolver cache-hit guards preserve existing rows in ordinary use.
Race/overwrite protection is not established by that existence check.

Before implementing database activation:

1. Inspect only the target table/column/constraint metadata read-only under
   explicit authorization; repository schema does not establish live schema.
2. Review a migration that retains complete old/new artifacts and provenance
   as append-only revisions. Do not put it into automatic startup execution.
3. In one explicit transaction, lock/check the targeted current artifact and
   supplied source fingerprints, archive the actual old row, record the
   proposed replacement and switch the current revision. A stale package must
   abort without replacing any row. Package hashes alone do not authorize it.
4. Reset row-level and group-level authority to proposed for generated
   replacements. Ordinary generation is now insert-only and cannot activate
   corrections. Its former upsert retained `validation_status`; do not restore
   that replacement path, which could preserve approval from another revision.
5. Test transaction failure/rollback and stale-source behavior on isolated
   PostgreSQL before any separately approved live correction. This package
   tooling does not claim those guarantees are already implemented.

Historical skill recalculation, automatic regeneration, external fetching,
detector changes and deployment remain separate operations. No migration or
live correction was executed for this local implementation.
