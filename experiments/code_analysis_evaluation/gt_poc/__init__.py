"""Ground-Truth Architecture POC (JSON-first, Phases 1–5).

Implements the pipeline described in
``experiments/code_analysis_evaluation/GROUND_TRUTH_ARCHITECTURE_SPEC.md``:

    ingest -> normalize -> deduplicate -> group families -> prepare
    independent labels -> hold out -> validate -> auditable JSON artifacts

Hard boundaries (by design — this is a POC):

* read-only use of the FROZEN shadow analyzer (no detector/technique/strategy
  /vocabulary/matcher changes);
* no database writes, no database reads on the default pipeline path
  (the DB-derived corpus is a committed snapshot);
* no LLM or network calls anywhere;
* no GT promotion, no active-version loading, no runtime integration.

All artifacts are deterministic: no wall-clock timestamps are written.  Any
date/time metadata belongs to the Phase 6 ``gt_versions`` rows.
"""

POC_VERSION = "1.0.0"
