# Qualification of generic legacy patterns

These detectors require linked relationships in one executable scope. A sum
of weak observations cannot substitute for that requirement. This is a bounded
static recognizer, not a correctness, complexity or optimality prover.

- `brute_force`: fresh enumeration drivers must feed candidate predicates,
  constructed outputs or bound recursive choices. A consuming window pointer,
  grid visitation, tree traversal or loop nesting alone is insufficient.
  Exhaustive subset output is supported and may be output-size optimal.
- `dp_state_machine`: distinct loop-carried state lanes must participate in a
  mutually dependent recurrence with a choice. Scalar snapshots and parallel
  assignment respect evaluation order; table lanes distinguish previous/current
  iterations. One-way totals and reporting extrema are insufficient. This rule
  concerns this multi-state pattern, not all forms of dynamic programming.
- `greedy_local`: a choice must affect subsequent working state, prefix-derived
  reward, reachable frontier or guarded adjacent propagation. Returning an
  extremum, updating a reporting best or using suggestive identifiers is
  insufficient. The supported relationships are explicit; they do not establish
  that every algorithm using such a step is globally optimal.

Local expression snapshots preserve branch boundaries. Unknown effects,
rebinding, mutable escapes and unsupported state shapes cause abstention rather
than borrowed evidence. This is intentionally not a general alias, call-effect,
monotonicity or complexity analysis. Unsupported syntax remains a coverage limit.

The shared checks are consumed by the real detectors before existing matching;
there is no problem-ID blacklist, detector veto, new threshold or dependency.
Independent qualified patterns may coexist. Existing evidence weights remain
heuristic 0–1 values; excluding unrelated evidence can change their totals.
Primitive facts remain available through observational Shadow analysis. Shadow
strategy/authority policy, scoring gates, feature defaults, vocabulary and cached
ground truth are unchanged. Absence of a qualified label is not a skill deficit.

Preparation's existing 33-pattern catalogue excludes the diagnostic
`brute_force` label. It therefore cannot currently prepare that label as a
problem expectation, even when exhaustive enumeration is appropriate. Do not
force it into another family or silently add a rated skill. The versioned
descriptive-approach contract retains such unscored proposals separately from
matchable requirements. Context-free analysis exposes qualified observations
without rating changes.

The original-submission assessment additionally qualifies these bounded forms:

- Hash lookup/counting links a locally created receiver to its loop operation.
  Membership in a different object, borrowed scopes, rebinding and mutable
  escapes cannot establish the link. A populated dictionary subsequently read
  by index is a lookup; mapping ranks to values is not frequency counting.
  Unit occurrence updates recognize `+= 1` and same-key assignment/get forms.
  As with platform-provided builtins, LeetCode snippets may omit a standard
  `Counter`/`defaultdict` import. An otherwise unbound standard constructor name
  plus linked occurrence updates is supported under that environment assumption;
  explicit nonstandard imports, local/outer bindings and shadowed factories
  defeat it. This is structural evidence, not proof of the runtime binding.
- Legacy variable windows use the shared boundary/content and guarded last-seen
  links already used by Shadow. Indexed reassignment alone is insufficient.
  Legacy recognition also retains `enumerate` element links and paired product
  multiplication/division maintenance. Product domain/correctness assumptions
  remain the solution's responsibility; these do not expand canonical strategy
  families or establish functional correctness.
- Rolling 1D recurrence supports two initialized scalar lanes, simultaneous
  shift-plus-sum updates, and consumption of a resulting lane. Unrelated totals,
  opaque calls, extra lane writes and unconsumed state do not qualify.
- Exhaustive contiguous subarray enumeration may reset a local set per start,
  extend it by the end-index element and aggregate its cardinality. A reset,
  unused set or unrelated element cannot supply this stateful candidate link.
- A local greedy choice may save an extremum's index during a scan and use that
  saved index for subsequent unit mutation of an input involved in the candidate.
  Rebinding the selected index or mutating an unrelated position abstains.
  Rescanning can still be too slow: this is no efficiency/optimality verdict.

The `prefix_sum` label requires additive accumulation (including subtraction
or weighted incoming values). Multiplying the accumulated prefix is a product
scan, not additive sum evidence. Valid or optimal product approaches must not
be judged deficient because this label does not cover them. Indexed and append
product scans therefore abstain; ordinary, renamed and weighted additive forms
retain detection. This corrects the older product-except-self test expectation
and contradictory multiplication acceptance; no corpus or stored row is relabeled.

Regression expectations use source-reviewed positives and near misses, paired
identifier renaming and actual analysis/matching. Published examples retain their
provenance and licence notices; submitted code is never executed as a test.

## Identifier-independent relationships

The independent friend-source assessment exposed additional name-based and
borrowed-evidence errors. Qualification now uses these local relationships:

- Prefix construction extends the **same destination's** preceding additive
  prefix. A neighboring previous-row DP value, a different list's last item,
  a reset destination, or an unrelated `get()` call is insufficient.
- Opposite pointers must be the two identities compared by one loop and must
  respectively advance and retreat. Changes to an unrelated scalar or a nested
  function cannot stand in for either pointer.
- Fast/slow requires unconditional local updates at different successor-hop
  counts. It supports `.next` links and a common indexed successor table
  (functional-graph Floyd). Equality alone and equal-speed intersection cursors
  do not qualify. The existing `pointer_names` evidence key is retained for API
  compatibility, but its description and weight now refer to structural pointer
  identities, never their spelling.
- Recursive DFS links an actual locally resolved recursive candidate to the
  current parameter's adjacency row, child collection, child link or grid
  expansion. An unrelated loop/visited-name cannot qualify array split recursion.
  BFS layers and hop propagation share scoped FIFO/expansion observations across
  the legacy level-order and shortest-path presentations. Named distance or
  visited variables do not confer evidence. No shortest-path correctness proof
  is claimed.
- Rotated binary search links a stable midpoint to one interval, one sequence's
  sorted-half decision, an ordered target-range predicate and its direct
  corresponding narrowing assignments. All midpoint-based boundary assignments
  must belong to supported range decisions. Unknown Boolean implications and
  nested unrelated guards abstain.
- Sequence DP links the outer table cell to earlier inner-loop positions through
  a min/max recurrence. A repeated rolling-row grid recurrence is not sequence
  DP merely because an index or table has a conventional name. Explicit row
  construction from the same history's prior row and repeated in-place row
  recurrences provide grid DP evidence. Normal platform builtin meanings,
  non-aliased table storage, valid loop bounds and normal problem domains remain
  assumptions; recognition does not prove them or functional correctness.
- Fixed offsets may be stable additive/subtractive expressions, consistently
  shared by initialization, loop start and outgoing index. This does not prove
  that a runtime width is positive. Literal nonpositive widths and changing
  offset operands abstain. Chained/unpacked zero initializers preserve actual
  assignment links for window boundaries.
- A monotonic stack is the popped receiver initialized in the same lexical
  block before the loop, including a class method. Another empty output list or
  a separate helper cannot supply its initialization; nested pop expressions
  remain operations on that receiver.

Legacy evidence keys `reversal_variable_names` and `pointer_names` are retained
for compatibility. Their evidence is now structural and identifier independent.
No ground truth, pattern taxonomy, matching threshold, authority, scoring policy
or feature-flag default changes follow from these detector qualifications.
