# Automated expectation preparation

Normal use must not require a person to verify each generated problem record.
Development testing and architectural review remain separate from app workflow.

## Current implementation

- `/prepare-problem` generates missing expectations and caches them in
  `problem_ground_truth`. Existing rows are reused; `/analyze` remains DB-only.
- `OPENROUTER_MODEL` and `OPENROUTER_MAX_TOKENS` select the preparation model and
  completion budget. Defaults remain `openai/gpt-4o-mini` and `1000`.
- Invalid settings make no provider request. Explicitly incomplete/failed
  completions and non-text content fail through the existing generation-error
  path before storage. Older payloads without finish metadata remain compatible.
- Existing shape, vocabulary and approach checks run before storage. They do
  not prove semantic correctness or that all valid approaches were enumerated.
- Generated definitions remain `llm_proposed`. No manual-approval queue is
  required to store or display them as proposed comparison references.

## Direction for subsequent implementation

1. Use the full available problem statement and constraints. Record source
   identity and completeness; a title alone is weak evidence for generation.
2. Request explicit alternative approaches and their combined requirements,
   allowing unsupported approaches to remain unrepresented without substituting
   a misleading supported pattern. Keep existing ONE_OF semantics.
3. Use automatic structural/consistency checks and, only if justified by a
   bounded comparison, an optional model critique. Model agreement and valid JSON
   are not independent verification of algorithm correctness.
4. Store generation provenance, input/prompt/model versions and coverage limits
   so cached output can be traced. This provenance extension is not implemented
   by the model-configuration change.
5. Keep generation costs attached to preparation, with shared cache reuse.
   Token limits are not a total spending cap. Current retries can make up to
   three requests; concurrent cache misses are not exactly-once generation.
   Spending controls and concurrency protection require a separate bounded task.
6. Handle old mistaken records through an explicit, versioned automated refresh
   operation with cost limits. Changing models does not silently regenerate,
   overwrite, relabel or promote existing rows.

## Authority boundary

Automatic preparation can produce useful proposed references without human
approval. It cannot label model output HUMAN_APPROVED or EXTERNAL_VERIFIED.
Existing scoring/product gates and feature defaults remain unchanged. Any new
policy allowing automated evidence to affect learner state or recommendations
requires an explicit architectural decision, not a per-record reviewer.

When evidence is insufficient, expose the limitation and abstain from a skill
penalty. Do not force detection to match generated labels or change labels to
improve evaluation metrics. A stronger model is a candidate to evaluate, not a
guarantee of correct ground truth.
