# Architecture Hardening M1 + M2 — Validation Report

**Scope:** M1 (normalized statement-operation dispatch) + M2 (shared relational-evidence layer, proof-of-architecture consumer: `sequential_accumulation`). No M3, no strategy-semantics changes, no ground-truth changes, no matcher changes, no new techniques, no name heuristics, no problem-ID logic. Public contracts (`StructuralFact`, `TechniqueEvidence`, `StrategyEvidence`, `MatchOutcome`) unchanged.

## What changed

| file | change |
|---|---|
| `shadow/fact_extractor.py` | **M1:** `_OPERATION_STATEMENTS = (Expr, Assign, AnnAssign, AugAssign)`; `_run_statement_operation_detectors` runs `queue_dequeue` + `stack_operation` once per operation statement (all forms incl. tuple-unpack). `_detect_equal_assignment` iterates normalized targets (multi-target `a = b = a+1` now supported). `visit_AnnAssign` emits `accumulator_update` for self-referential annotated assignments (`syntax_form: "annotated_equal_sign"`). `_detect_stack_operation` extended to the family (was Expr-only). |
| `shadow/relations.py` | **M2 (new):** `SubmissionRelations` + `build_relations(ast)` — `updated_in_loop`, `used_as_subscript_index`, `def_use_pairs`, `collection_ops` (append/pop/popleft/pop(0)/pop(n)/heappush/heappop with position; heap ops resolve the first-argument collection, not the `heapq` receiver), `iterated_in_for`. Deterministic, one pass, no CFG/SSA. |
| `shadow/techniques.py` | `detect_techniques(facts, relations=None)`. `sequential_accumulation` migrated: relations oracle (`updated_in_loop`) selects the accumulator variable to join; the original fact-join gate still decides admissibility; **verbatim fallback path** runs when relations are absent or yield nothing. |
| `shadow/shadow_runner.py` | Computes relations once per submission; exports `relations_version`. |
| `shadow/persistence.py` | `rerun_derivation(..., relations=None)` — optional; omitted ⇒ fallback ⇒ identical results for stored-fact re-derivation. |

## M1 coverage closed (was silently invisible before)

- `node = stack.pop()` / `total: int = total + 1` / `total += stack.pop()` — all extracted now.
- Discrimination preserved in every form: `pop()`/`pop(n)`/heap ops are never queue dequeues.
- `queue_dequeue`/`stack_operation` attributes byte-identical for previously supported forms.

## Validation

1. **New generalized tests:** `test_m1_m2_architecture.py` — **32 passed** (dispatch parity, relations semantics, fallback contract, adversarial "relations cannot create detections" check, runner integration incl. graceful degradation).
2. **Shadow suite:** **615 passed** (was 583; +32 = exactly the new tests, all originals green).
3. **Full repository suite:** **1489 passed / 1 failed** — only the known pre-existing legacy `prefix_sum` detector failure. Baseline was 1457/1 ⇒ +32, zero movement.
4. **Corpus before/after (71 submissions, HEAD extractor+techniques vs working tree + relations, live DB groups):**
   - fact-multiset changes: **0**
   - technique presence changes: **0**
   - strategy-set changes: **0**
   - verdict changes: **0** (35 CONFIRMED / 16 UNRESOLVED / 19 NO_GROUPS both sides; 0 new CONTRADICTED)
   - `sequential_accumulation` evidence citations: 23 submissions changed, **all strict subsets** (0 added evidence) — the relations oracle tightens citations by dropping superfluous extra-accumulator facts; same verdict weight.
5. **End-to-end harness** (`--force`, 46 DB submissions, live groups): identical flag distribution; single verdict delta (`db-244`, LC 102: UNRESOLVED → CONFIRMED via `bfs_shortest_path` at 0.800) is the already-committed **N2** change (`HEAD = 93176cb fix: generalize BFS queue fact extraction`) measured against a pre-N2 result file — not an M1+M2 effect. The commit-scoped diagnostic isolates M1+M2 to exactly zero changes.

## Acceptance criteria

| criterion | result |
|---|---|
| Existing tests green | ✅ 615 shadow / 1489 repo (1 pre-existing failure unchanged) |
| No unexpected verdict changes | ✅ 0 changes attributable to M1+M2 |
| Sequential-accumulation behavioral equivalence | ✅ same presence, same confidence, evidence strict-subset only; fallback preserves exact legacy outputs (incl. pinned trivial-counter and hand-built-facts cases) |
| Relation layer actually consumed | ✅ proven by the 23 strict-subset citation tightenings (fallback cannot produce them; unused code could not cause them) |
| Public contracts unchanged | ✅ |
| No M1/M2 scope creep | ✅ stopped before M3 |

**Stopped.** No M3 (allowlist retirement), no detector semantics beyond the migrated consumer, no ground-truth or matcher edits.
