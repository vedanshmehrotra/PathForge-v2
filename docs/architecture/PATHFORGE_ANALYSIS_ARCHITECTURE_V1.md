# PathForge Analysis Architecture v1

## 1. Purpose

This document freezes the first target architecture for PathForge's code-analysis and solution-matching boundary.

The purpose is to replace the current flat model:

```text
Code
→ AST pattern detectors
→ pattern IDs
→ exact pattern matching
→ PASS / FAIL
```

with:

```text
Code
→ structural facts
→ technique evidence
→ strategy evidence
→ solution-group satisfaction
→ CONFIRMED / UNRESOLVED / CONTRADICTED
→ existing evidence/authority gate
→ ELO / gaps / recommendations
```

The architecture is intentionally limited in scope. It is designed to remove the current category error where structural observations, reusable techniques, and algorithmic strategies are treated as interchangeable pattern labels.

This is an architecture specification, not an implementation plan.

---

## 2. Problems This Architecture Must Solve

The current system has demonstrated several failure modes:

1. **False negatives from syntax dependence**
   - Equivalent `for` and `while` implementations are treated differently.
   - Equivalent update expressions such as `i += 1` and `i = i + 1` may be treated differently.
   - Variable naming can influence detection.
   - Equivalent AST shapes may not be recognized.

2. **Incidental behavior mistaken for algorithmic classification**
   - DFS/BFS may use a visited set without being a hash-map algorithm.
   - Sliding window may use two moving pointers without being the same strategy as opposite-direction two pointers.
   - DP may use accumulation without being a prefix-sum solution.
   - Almost every non-trivial algorithm may traverse a collection.

3. **Flat taxonomy problems**
   - `array_traversal` is a structural primitive, not a meaningful primary algorithm label.
   - `hash_map_lookup` describes reusable data-structure behavior rather than one algorithmic strategy.
   - `prefix_sum` is better treated as a reusable technique.
   - Some concepts, such as `two_pointers_opposite`, are specific enough to support strategy-level reasoning.

4. **Ground-truth incompleteness or error**
   - A single incorrect or incomplete ground-truth label can cause a correct submission to be treated as a mismatch.
   - Multiple legitimate solution approaches cannot be represented safely by one flat pattern list.

5. **Overconfident matching**
   - The system must not convert lack of evidence into a confident contradiction.
   - `UNRESOLVED` must be a normal, non-punitive result.

---

## 3. Architectural Principles

### 3.1 Canonical truth is structural evidence only

The canonical persisted analysis artifact is the set of deterministic structural facts extracted from the submitted code.

Technique evidence, strategy evidence, satisfaction scores, and match outcomes are derived projections.

They are versioned and re-derivable. They are not canonical truth.

This is required for taxonomy evolution. When technique or strategy definitions change, the system can re-run derivation against existing structural facts instead of treating old labels as immutable truth.

### 3.2 Facts do not compete

A submission may contain many simultaneously true facts.

For example, a DFS solution may contain:

- recursion
- collection membership
- set construction
- branch traversal
- visited-state updates

These facts do not compete for one "correct pattern" slot.

### 3.3 Techniques are reusable evidence

A technique can appear in many strategies.

A technique is not, by itself, proof that a particular strategy was used.

Technique evidence is therefore non-exclusive.

### 3.4 Strategies are derived compositions

A strategy is inferred from a specific combination of techniques plus explicit structural/contextual constraints.

A single low-level signal must not be sufficient to promote a strategy.

### 3.5 Primary strategy is a projection

`primary_strategy` is not canonical ground truth.

It is a derived, confidence-aware presentation result that may be null.

A submission may have several meaningful strategy candidates or no sufficiently confident primary strategy.

### 3.6 Unknowns are first-class

The system must be able to say:

```text
CONFIRMED
UNRESOLVED
CONTRADICTED
```

rather than forcing every submission into a binary match/no-match outcome.

---

## 4. Layer 1: Structural Facts

Structural facts are deterministic, mechanically decidable observations.

A structural fact must satisfy this test:

> Can it be extracted without guessing the algorithmic intent?

If not, it does not belong in the structural-fact layer.

### 4.1 Initial fact vocabulary

The initial vocabulary should remain intentionally small.

Examples:

| Fact | Meaning |
|---|---|
| `loop_shape` | `for` / `while`, nesting, boundedness where mechanically decidable |
| `constant_step_update` | variable changed by a literal constant step |
| `indexed_access` | variable used in collection indexing |
| `linked_structure_traversal` | explicit linked/tree-style attribute traversal such as `.next`, `.left`, `.right` |
| `membership_check` | `in` / `not in` comparison |
| `container_type_observation` | list/dict/set/heap/queue/etc. where statically knowable |
| `container_operation` | lookup, insert, delete, push, pop, etc. |
| `accumulator_update` | variable updated from its prior value through a recognized operator |
| `self_recursive_call` | function directly calls itself |
| `early_termination` | loop/function exits before ordinary completion |
| `control_dependency` | a value influences a branch/loop condition |
| `return_dependency` | a value contributes to returned output |
| `sortedness_fact` | explicit evidence of sorting or problem-context guarantee |
| `def_use_relation` | local data-flow relation between definitions and uses |
| `pointer/index direction` | mechanically observed direction for a known index/update form |

### 4.2 Fact-layer restrictions

The fact layer must NOT directly emit:

- `binary_search`
- `hash_map_lookup`
- `prefix_sum`
- `BFS`
- `DFS`
- `sliding_window`

as final algorithm labels.

It emits the underlying evidence.

### 4.3 Syntax normalization

Equivalent surface syntax should be normalized here.

Examples:

```text
i += 1
i = i + 1
```

should map to the same canonical constant-step fact when both are mechanically recognized.

Normalization belongs before technique/strategy evaluation so higher layers do not accumulate syntax-specific rules.

### 4.4 Local type information

The semantic analysis layer may provide limited, intraprocedural type inference where needed to distinguish facts such as:

```text
x in list
x in set
x in dict
```

This is specifically important for avoiding incorrect data-structure interpretations.

The architecture does not require a general-purpose type inference engine.

---

## 5. Layer 2: Technique Evidence

Techniques are reusable computational idioms constructed from multiple structural facts.

### 5.1 Technique admission rule

A concept should be admitted as a technique only if:

1. It is composed from multiple lower-level facts.
2. It recurs as a genuine component across more than one strategy/problem context.
3. Its presence does not, by itself, imply one unique algorithmic strategy.
4. Its evidentiary specificity is understood and bounded.

This rule exists to prevent taxonomy-by-accretion.

### 5.2 Initial technique examples

Potential examples:

- `two_pointer_scan`
- `prefix_sum_accumulation`
- `sliding_window_maintenance`
- `boundary_narrowing`
- `memoization`
- `visited_tracking`
- `frequency_counting`

These are candidates for the first technique vocabulary. The final list must be justified against the above admission rule.

### 5.3 Technique evidence contract

```json
{
  "submission_id": "...",
  "technique_id": "...",
  "technique_version": "...",
  "supporting_fact_ids": ["..."],
  "presence_confidence": 0.0,
  "centrality": 0.0
}
```

`presence_confidence` answers:

> Is the underlying technique evidence actually present?

`centrality` answers:

> How central is this evidence to the observed computation?

These are deliberately separate.

They must not be prematurely collapsed into one scalar.

---

## 6. Layer 3: Strategy Evidence

Strategies are higher-level, derived concepts with a recognizable controlling structure.

Examples include:

- `binary_search`
- `sliding_window`
- `two_pointers_opposite`
- `bfs_shortest_path`
- `dfs_backtracking`
- `dp_top_down_memo`
- `dp_bottom_up`
- `union_find`

### 6.1 Strategy rule

A strategy must be defined by:

- a combination of technique evidence
- required structural constraints
- optional supporting evidence
- relevant problem context when necessary

A single technique must not be sufficient to classify a strategy unless that is explicitly justified.

### 6.2 Problem context

Some strategy inference depends on facts about the problem itself.

Problem context therefore participates in strategy inference:

```text
code facts
+
problem facts
→ strategy evidence
```

Initial problem context should be sparse and represented as 3-state signals:

```text
confirmed
absent
unknown
```

Initial candidate tags include:

- `sorted_input`
- `bounded_range`
- `uniqueness_guaranteed`
- `duplicates_allowed`
- `complexity_hint`

Unknown is distinct from absent.

A missing problem tag must not silently suppress a valid strategy.

---

## 7. Primary Strategy

`primary_strategy` is a derived projection only.

It should be computed when:

- one strategy candidate clearly dominates
- its evidence exceeds the required confidence
- the relevant solution/strategy definitions permit the inference

Otherwise:

```text
primary_strategy = null
```

The full ranked strategy evidence remains available for explanation and analysis.

No canonical comparison logic may depend on a persisted `primary_strategy` field.

---

## 8. Solution Groups

A problem may have multiple accepted solution approaches.

Each approach is represented independently as a solution group.

### 8.1 Initial schema

```json
{
  "group_id": "...",
  "version": 1,
  "problem_id": "...",
  "required": ["..."],
  "optional": ["..."],
  "excluded": ["..."],
  "threshold": 0.0,
  "authority_tier": "...",
  "provenance": ["..."]
}
```

### 8.2 Initial semantics

`required`

All required evidence conditions must be sufficiently supported.

`optional`

Supporting evidence that can raise confidence but cannot independently satisfy the group.

`excluded`

Evidence that directly argues against this specific solution approach.

`threshold`

Minimum satisfaction required to classify the group as satisfied.

### 8.3 Deliberately deferred

The v1 schema does not include:

- general OR / disjunction syntax
- group inheritance
- arbitrary conditional logic
- complex expression trees

If a real problem later requires one of these, extend the model based on evidence rather than speculative design.

---

## 9. Matching

The matching engine changes from pattern-ID equality to solution-group satisfaction.

For each solution group:

1. Evaluate required evidence.
2. Evaluate optional evidence.
3. Evaluate excluded evidence.
4. Apply the group's threshold.
5. Produce a satisfaction result.
6. Preserve the evaluated group version.

The result is not simply:

```text
pattern == expected_pattern
```

It is:

```text
does the submission satisfy at least one accepted approach?
```

### 9.1 Possible outcomes

`CONFIRMED`

At least one authoritative or sufficiently trusted solution group is satisfied.

`UNRESOLVED`

Evidence is insufficient, ground truth is not authoritative enough, or no solution group is adequately satisfied.

`CONTRADICTED`

A sufficiently authoritative solution group establishes a meaningful conflict with the observed evidence.

A low-authority/bootstrap group must not generate `CONTRADICTED`.

### 9.2 Borderline results

A result close to a threshold should be capable of being classified as unresolved rather than creating a brittle cliff at one numeric value.

This preserves uncertainty instead of converting small score changes into discontinuous user consequences.

---

## 10. Ground-Truth Authority

Ground truth has its own evidence hierarchy.

### 10.1 Bootstrap

Potential sources:

- candidate generated by the free LLM
- multiple independent LLM generations
- official/editorial source where available

Agreement across multiple independent generations can increase confidence, but is not proof against systematic model blind spots.

### 10.2 Authority rule

Bootstrap-tier solution groups must not produce authoritative contradiction.

They can support:

- analysis
- candidate matching
- future evidence collection

They must not silently punish the user.

### 10.3 Higher-authority sources

An editorial or reviewed source can receive stronger authority.

Repeated unresolved submission clusters can identify likely ground-truth coverage gaps, but clusters do not automatically prove algorithmic correctness.

Human review is not designed as a continuous per-problem workflow in v1.

---

## 11. Evidence Persistence

The canonical persisted submission artifact is the structural fact set.

Minimum contract:

```json
{
  "submission_id": "...",
  "fact_id": "...",
  "fact_type": "...",
  "ast_ref": "...",
  "attributes": {},
  "extractor_version": "..."
}
```

Technique and strategy evidence may be persisted as derived artifacts for performance and explanation, but they are not canonical.

Definitions are versioned.

Each derived record references:

- definition/version
- supporting evidence
- derivation version

This allows a taxonomy revision to re-derive higher-level interpretation from stable lower-level facts.

---

## 12. Taxonomy Versioning

Structural facts are stable observations tied to an extractor version.

Technique and strategy definitions are versioned data.

Rules:

1. Do not mutate historical definitions in place.
2. Introduce a new version when semantics change.
3. Preserve old versions for historical interpretation.
4. Re-derive higher-level evidence from persisted facts when needed.
5. Defer a generic migration engine.
6. When a real split occurs, define an explicit mapping or mark the old evidence as ambiguous.

Taxonomy evolution must not silently corrupt historical evidence.

---

## 13. ELO and Learning Analytics

True ELO changes are intentionally deferred until:

- taxonomy churn stabilizes
- ground-truth reliability improves
- the new analysis contract has real-world validation

The architecture should preserve technique-level evidence so future learning analytics can operate at that granularity.

`primary_strategy` is not the primary ELO unit.

Strategy-level skill can later be derived from technique evidence.

No new ELO implementation is part of this architecture freeze.

---

## 14. Existing Downstream Pipeline

The redesigned analysis boundary should preserve the existing outer pipeline:

```text
analysis
→ matching
→ persistence
→ authority gate
→ ELO / topic profiles / gaps / recommendations
```

The downstream systems should consume the new tri-state/authority-aware analysis output rather than reconstructing algorithmic meaning from raw pattern IDs.

The evidence/authority system remains a core safety boundary.

Low-authority or unresolved analysis must remain non-punitive.

---

## 15. Failure Behavior

### Correct code with incomplete ground truth

Result:

```text
UNRESOLVED
```

not an unjustified contradiction.

### Code with unusual but valid structure

Persist the structural facts.

If no current technique/strategy definition recognizes them:

```text
UNRESOLVED
```

This is expected behavior.

### Incorrect or low-authority ground truth

It cannot confidently punish the user.

### Multiple accepted solution groups

Evaluate each group independently.

A single group match is sufficient for confirmation if the group's authority allows it.

No requirement exists that all accepted groups agree.

---

## 16. Add Two Numbers: Expected Behavior

The architecture should extract facts such as:

- linked-structure traversal
- value accumulation
- carry/state propagation
- node construction

It should not classify this merely because two variables move.

A valid solution group for the problem should describe the required evidence for the accepted approach.

A previous erroneous `linked_list_reversal` label must not be able to force a correct implementation into a false contradiction.

If no authoritative group adequately describes the actual approach:

```text
UNRESOLVED
```

is the correct safe outcome.

---

## 17. Problem 2996: Expected Behavior

The architecture should extract facts such as:

- indexed traversal
- sequential accumulation
- list membership
- repeated increment/search
- while-loop structure

It should not incorrectly infer hash-map behavior from list membership.

If the current technique vocabulary does not contain an appropriate technique for the second-loop idiom, the correct result is:

```text
UNRESOLVED
```

not a fabricated strategy label.

The stored structural facts remain available for future definition updates.

A problem-specific detector is explicitly prohibited.

---

## 18. What Is In Scope for V1

1. Deterministic structural fact extraction.
2. Syntax normalization for equivalent low-level forms.
3. Minimal local type inference where necessary.
4. Local def-use / return-dependency analysis.
5. Technique definitions as versioned data.
6. Strategy definitions as versioned data.
7. One reusable evidence-satisfaction evaluator.
8. Solution groups using required/optional/excluded/threshold.
9. Tri-state outcomes.
10. Persistent structural facts.
11. Propagation of the existing authority gate.
12. Backward-compatible integration with the existing outer pipeline.

---

## 19. Explicitly Deferred

The following are intentionally out of scope:

- runtime LLM verification
- continuous human review
- full CFG framework
- interprocedural analysis
- generic logic/constraint language
- OR/disjunction in solution groups
- group inheritance
- generic taxonomy migration engine
- automatic taxonomy discovery
- automatic clustering as proof of correctness
- production ELO redesign
- technique-level ELO implementation
- broad problem-context ontology
- semantic/competition heuristics for the old flat pattern taxonomy
- production activation of the existing semantic shadow scorer

---

## 20. Architecture Invariants

The implementation must never violate these:

1. Structural facts are canonical; higher-level labels are derived.
2. A low-level fact never directly authorizes a strategy classification.
3. Multiple facts may be simultaneously true.
4. Techniques are non-exclusive evidence.
5. Strategies require compositional evidence.
6. Primary strategy is a projection, not canonical truth.
7. Multiple solution groups are first-class.
8. Exact pattern-ID equality is not the definition of a valid solution.
9. Unresolved is a normal and non-punitive outcome.
10. Bootstrap ground truth cannot confidently contradict a user.
11. Lower-confidence analysis cannot silently affect ELO, gaps, recommendations, or other authoritative downstream behavior.
12. Higher-level definitions are versioned and re-derivable from stable evidence.

---

## 21. Definition of Done for the Architecture

The architecture is considered frozen when:

- the data contracts above are agreed
- the fact vocabulary has an explicit inclusion rule
- initial technique and strategy definitions are identified
- at least the Add Two Numbers and 2996 examples can be represented without special-case detectors
- one deliberately ambiguous multi-solution problem can be represented
- no step requires a hard-coded pattern-ID equality
- unresolved behavior is explicitly supported
- authority behavior is explicitly connected to the existing downstream gate
- deferred items remain deferred

Only after this point should implementation begin.

---

## 22. Final Architecture Decision

**Decision: SIMPLIFY AND ADOPT**

PathForge will move from flat pattern classification toward:

```text
Deterministic facts
→ reusable techniques
→ derived strategies
→ versioned accepted solution groups
→ satisfaction matching
→ confirmed / unresolved / contradicted
→ existing authority gate
→ downstream learning systems
```

The architecture deliberately keeps the lower-level evidence stable and makes higher-level interpretation versioned and re-derivable.

This is intended to stop the current cycle of adding pattern-specific heuristics whenever a new valid implementation causes a false negative, while preserving the existing PathForge pipeline wherever it is already sound.
