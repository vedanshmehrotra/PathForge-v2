# Deterministic Semantic Analysis Architecture for PathForge

## Executive Summary

PathForge's current AST detectors are highly precise (99.8%) but fragile: they depend on specific loop forms (`for` vs `while`), variable names, and AST shapes. Real user submissions fail because the code is correct but structurally different from what detectors expect.

This document proposes a **deterministic semantic feature layer** that sits above raw AST detectors, extracting normalized program features that are invariant to superficial code differences. The existing detectors become consumers of these features instead of directly inspecting raw AST shapes.

---

## 1. Current Detector Limitations (Demonstrated by Real Failures)

### Failure A: Problem 2996 (Zero Detections)

```python
class Solution:
    def missingInteger(self, nums):
        i = 1
        summ = nums[0]
        while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
            summ += nums[i]
            i += 1
        while summ in nums:
            summ += 1
        return summ
```

**What detectors see:**
- `array_traversal`: Requires `ast.For` → gets `ast.While` → misses
- `hash_map_lookup`: Requires explicit `dict()`/`set()` creation → none present → misses
- `prefix_sum`: Requires specific assignment pattern `prefix[i] = prefix[i-1] + nums[i]` → gets `summ += nums[i]` → misses

**What a human sees:**
- Array traversal with index (`i` moves through `nums`)
- Running sum accumulator (`summ += nums[i]`)
- Membership test (`summ in nums`)
- Sequential increment (`i += 1`)

### Failure B: Add Two Numbers (Wrong Ground Truth)

The ground truth says `linked_list_reversal` but the correct pattern is `two_pointers_same`. This is a data quality issue, not a detector issue, but it demonstrates that even correct detection can be defeated by wrong ground truth.

### Systematic Weaknesses

| Weakness | Root Cause | Affected Detectors |
|----------|-----------|-------------------|
| While-loop blindness | Detectors only check `ast.For` | array_traversal, sliding_window, most loop-based detectors |
| Name dependence | Detectors check variable names like `left`, `right`, `i`, `j` | two_pointers, binary_search, sliding_window |
| Explicit data structure requirement | Detectors require `dict()`, `set()`, `[]` creation | hash_map_lookup, prefix_sum |
| Single AST shape | Detectors expect one specific code pattern | All detectors |
| No semantic understanding | Detectors match syntax, not meaning | All detectors |

---

## 2. Proposed Semantic Representation

### Core Principle

Extract **features that are invariant to superficial code differences** while preserving **algorithmic meaning**.

### Feature Categories

```
Code
  ↓
AST Parsing
  ↓
┌─────────────────────────────────────────┐
│  Normalization Layer                    │
│  - Loop form normalization              │
│  - Comparison normalization             │
│  - Variable role inference              │
│  - Expression normalization             │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│  Feature Extraction Layer               │
│  - Control-flow features                │
│  - Data-flow features                   │
│  - Data-structure usage features        │
│  - Higher-level semantic signals        │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│  Pattern Scoring                        │
│  - Rule-based scoring (deterministic)   │
│  - OR: ML classifier (optional)         │
└─────────────────────────────────────────┘
  ↓
Pattern → Confidence
  ↓
MatchingEngine
```

---

## 3. Normalization Layer Design

### 3.1 Loop Normalization

**Problem:** `for i in range(len(nums))` and `while i < len(nums): ... i += 1` are semantically equivalent.

**Solution:** Classify loops by semantic intent, not syntax.

```python
@dataclass
class NormalizedLoop:
    loop_type: str          # 'counted', 'collection', 'condition', 'infinite'
    iterator_var: str       # variable that advances
    bound_expr: str         # normalized termination condition
    step_expr: str          # how iterator advances
    body_complexity: int    # nesting depth
    has_early_exit: bool    # break/continue/return in body
```

**Detection rules:**
- `for x in range(n)` → `counted` with `step=1`
- `while i < len(arr): ... i += 1` → `counted` with `step=1`
- `for x in collection` → `collection` iteration
- `while condition:` → `condition` loop

### 3.2 Comparison Normalization

**Problem:** `a < b` and `not (a >= b)` are equivalent. `a == b` and `a is b` differ semantically.

**Solution:** Normalize comparisons to canonical forms.

```python
def normalize_comparison(node: ast.Compare) -> str:
    """Normalize a comparison to canonical form."""
    # a < b → less_than(a, b)
    # a > b → less_than(b, a)  (swap operands)
    # not (a < b) → greater_equal(a, b)
    # a <= b → less_equal(a, b)
    # a == b → equal(a, b)
    # a != b → not_equal(a, b)
    # a in collection → member(a, collection)
    pass
```

### 3.3 Variable Role Inference

**Problem:** Detectors check for variable names like `left`, `right`, `i`, `j`. Different programmers use different names.

**Solution:** Infer semantic roles from usage patterns, not names.

```python
@dataclass
class VariableRole:
    name: str
    role: str              # 'index', 'accumulator', 'pointer', 'bound', 'result', 'temp'
    initialized_from: str  # where the variable gets its initial value
    updated_in_loop: bool  # whether the variable changes in a loop
    update_pattern: str    # 'increment', 'decrement', 'accumulate', 'conditional', 'none'
    compared_to: list      # what the variable is compared against
```

**Role inference rules:**
- Variable initialized to `0` or `1` and incremented in loop → `index`
- Variable initialized to `nums[0]` and updated with `+=` → `accumulator`
- Variable compared against `len(collection)` → `bound`
- Variable assigned from function return → `result`
- Variable used in `x = x.next` → `pointer`

### 3.4 Expression Normalization

**Problem:** `i + 1` and `1 + i` are equivalent. `len(nums) - 1` and `len(nums) - 1` are identical.

**Solution:** Normalize expressions to canonical forms.

```python
def normalize_expression(node: ast.expr) -> str:
    """Normalize an expression to canonical string form."""
    # Sort commutative operands: i + 1 → 1 + i
    # Normalize comparisons: a < b → less_than(a, b)
    # Simplify double negation: not not x → x
    # Normalize method calls: x.append(y) → append(x, y)
    pass
```

---

## 4. Control-Flow Features

### 4.1 Loop Structure Features

```python
@dataclass
class LoopFeatures:
    # Loop count and types
    total_loops: int
    for_loops: int
    while_loops: int
    nested_loops: int
    
    # Loop relationships
    has_counter_loop: bool      # loop with explicit counter variable
    has_collection_loop: bool   # loop over collection
    has_condition_loop: bool    # while with complex condition
    has_early_exit: bool        # break/continue/return in loop body
    
    # Loop bounds
    bounds_use_len: bool        # loop bound involves len()
    bounds_use_comparison: bool # loop bound is a comparison
    bounds_use_membership: bool # loop bound involves `in` operator
    
    # Pointer movement
    single_direction_traversal: bool  # pointer moves one direction
    bidirectional_traversal: bool     # pointers move toward each other
    differential_speed: bool          # two pointers with different speeds
```

### 4.2 Branch Structure Features

```python
@dataclass
class BranchFeatures:
    total_ifs: int
    has_early_return: bool
    has_nested_conditions: bool
    has_boundary_check: bool    # if i < len(arr) or similar
    has_membership_check: bool  # if x in collection
    has_comparison_chain: bool  # if a < b < c
```

### 4.3 Recursion Features

```python
@dataclass
class RecursionFeatures:
    is_recursive: bool
    recursive_calls: int
    has_base_case: bool
    call_pattern: str          # 'linear', 'tree', 'exponential'
```

---

## 5. Data-Flow Features

### 5.1 Variable Analysis

```python
@dataclass
class DataFlowFeatures:
    # Variable roles
    index_variables: list       # variables used as array indices
    accumulators: list          # variables that accumulate values
    pointers: list              # variables that traverse structures
    bounds: list                # variables used in loop conditions
    results: list               # variables returned
    
    # Mutation patterns
    has_in_place_mutation: bool # modifies input data structure
    has_separate_output: bool   # builds new data structure
    
    # State reuse
    has_dp_state: bool          # references previous computation results
    has_memoization: bool       # caches computed results
    has_running_state: bool     # maintains state across iterations
```

### 5.2 Value Propagation

```python
@dataclass
class PropagationFeatures:
    # How values flow through the program
    has_accumulation: bool      # running sum/product/count
    has_pointer_movement: bool  # x = x.next or i += 1
    has_state_transition: bool  # finite state machine pattern
    has_dependency_chain: bool  # value depends on previous iteration
```

---

## 6. Data-Structure Usage Features

### 6.1 Collection Semantics

```python
@dataclass
class CollectionFeatures:
    # What data structures are used
    uses_array: bool
    uses_linked_list: bool      # .next attribute access
    uses_stack: bool            # push/pop (append/pop on list)
    uses_queue: bool            # deque operations
    uses_heap: bool             # heapq operations
    uses_tree: bool             # .left/.right attribute access
    uses_graph: bool            # adjacency list/dict
    
    # How collections are accessed
    has_indexed_access: bool    # collection[i]
    has_membership_test: bool   # x in collection
    has_sequential_access: bool # iterating in order
    has_random_access: bool     # arbitrary index access
    
    # Collection operations
    has_insert: bool
    has_delete: bool
    has_search: bool            # linear search in collection
    has_sort: bool
```

### 6.2 Data Structure Detection (Beyond Names)

**Problem:** Current detectors check for `dict()`, `set()`, `[]` creation. But Python code often uses collections without explicit creation:
- `x in some_list` → membership test without `set()` creation
- `x.append(y)` → stack behavior
- `x.pop(0)` → queue behavior
- `heapq.heappush(x, y)` → heap behavior

**Solution:** Detect usage patterns, not just creation patterns.

```python
def detect_collection_usage(tree: ast.AST) -> CollectionFeatures:
    """Detect how collections are actually used, not just how they're created."""
    features = CollectionFeatures()
    
    for node in ast.walk(tree):
        # Stack behavior: append + pop
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'append':
                    features.has_insert = True
                elif node.func.attr == 'pop':
                    features.has_delete = True
        
        # Membership test: x in collection
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, ast.In):
                    features.has_membership_test = True
        
        # Linked list traversal: x.next
        if isinstance(node, ast.Attribute):
            if node.attr in ('next', 'left', 'right'):
                features.uses_linked_list = True
        
        # Heap operations: heapq.*
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'heapq':
                        features.uses_heap = True
    
    return features
```

---

## 7. Higher-Level Semantic Signals

### 7.1 Algorithmic Pattern Signals

```python
@dataclass
class AlgorithmicSignals:
    # Two pointers
    has_two_bounds: bool           # two variables bounding a range
    bounds_converge: bool          # bounds move toward each other
    has_differential_speed: bool   # fast/slow pointer pattern
    
    # Binary search
    has_midpoint_calculation: bool # mid = (lo + hi) // 2
    has_partition_decision: bool   # if arr[mid] < target
    has_bound_update: bool         # lo = mid + 1 or hi = mid - 1
    
    # Sliding window
    has_window_bounds: bool        # left and right pointers
    window_expands: bool           # right += 1
    window_contracts: bool         # left += 1
    has_window_state: bool         # running sum/count in window
    
    # Dynamic programming
    has_state_table: bool          # dp = [0] * n or similar
    has_state_dependency: bool     # dp[i] depends on dp[i-1]
    has_optimal_substructure: bool # recursive relation
    
    # Graph algorithms
    has_visited_set: bool          # visited = set()
    has_queue: bool                # queue for BFS
    has_stack: bool                # stack for DFS
    has_recursion: bool            # recursive calls
    
    # Greedy
    has_sorting: bool              # sorted(arr) or arr.sort()
    has_local_choice: bool         # if/else choosing between options
    has_iteration_over_sorted: bool
```

### 7.2 Confidence Scoring

```python
def compute_pattern_scores(features: SemanticFeatures) -> dict:
    """Compute confidence scores for each pattern based on extracted features."""
    scores = {}
    
    # Two pointers
    score = 0.0
    if features.loop_features.bidirectional_traversal:
        score += 0.4
    if features.algorithmic_signals.has_two_bounds:
        score += 0.3
    if features.algorithmic_signals.bounds_converge:
        score += 0.3
    scores['two_pointers_opposite'] = min(score, 1.0)
    
    # Hash map lookup
    score = 0.0
    if features.collection_features.has_membership_test:
        score += 0.3
    if features.collection_features.has_indexed_access:
        score += 0.2
    if features.data_flow_features.has_accumulation:
        score += 0.2
    scores['hash_map_lookup'] = min(score, 1.0)
    
    # Array traversal
    score = 0.0
    if features.loop_features.has_counter_loop:
        score += 0.3
    if features.collection_features.has_sequential_access:
        score += 0.3
    if features.data_flow_features.has_pointer_movement:
        score += 0.2
    scores['array_traversal'] = min(score, 1.0)
    
    return scores
```

---

## 8. Comparison of Architecture Approaches

### Approach A: Continue Expanding Hand-Written Detectors

| Aspect | Assessment |
|--------|-----------|
| Recall improvement | Low — each fix is local, doesn't address systemic issues |
| Precision risk | Low — existing precision preserved |
| Complexity | Low per detector, high total (36+ detectors) |
| Interpretability | High — each detector is understandable |
| Data requirements | None |
| Runtime cost | Low — same as current |
| Maintainability | Poor — 36 detectors with overlapping logic |
| **Suitability** | **Poor** — doesn't solve the root cause |

**Verdict:** Continue as stopgap, but not the long-term solution.

### Approach B: Shared Deterministic Semantic Feature Layer

| Aspect | Assessment |
|--------|-----------|
| Recall improvement | High — addresses systemic loop-form, name, and shape blindness |
| Precision risk | Medium — feature extraction is deterministic but scoring needs calibration |
| Complexity | Medium — one feature layer, ~30 detectors become feature consumers |
| Interpretability | High — features are human-readable, scoring is transparent |
| Data requirements | None (rule-based scoring) |
| Runtime cost | Low — one AST walk for features, then simple scoring |
| Maintainability | Good — features are reusable, detectors become thin wrappers |
| **Suitability** | **Excellent** — matches PathForge's requirements |

**Verdict:** Recommended. Addresses root cause with minimal complexity.

### Approach C: Semantic Features + Classical ML Classifier

| Aspect | Assessment |
|--------|-----------|
| Recall improvement | Highest — ML can learn complex feature interactions |
| Precision risk | Medium-High — ML can overfit to training data |
| Complexity | High — feature extraction + model training + calibration |
| Interpretability | Medium — features are interpretable, but model weights are opaque |
| Data requirements | Needs labeled training data (100+ examples per pattern) |
| Runtime cost | Low — inference is fast with scikit-learn |
| Maintainability | Medium — model needs retraining as patterns evolve |
| **Suitability** | **Good** — but adds unnecessary complexity for current scale |

**Verdict:** Future option. Start with Approach B, add ML later if needed.

### Recommendation

**Start with Approach B.** It solves the root cause (systemic AST blindness) without adding dependencies or training data requirements. The feature layer is reusable and testable. ML can be added later if rule-based scoring proves insufficient.

---

## 9. Recommended Architecture

### Component Design

```
src/
  ast_detection/
    semantic/
      __init__.py
      normalizer.py          # Loop, comparison, expression normalization
      control_flow.py        # Loop, branch, recursion features
      data_flow.py           # Variable role, propagation features
      collection_usage.py    # Data structure usage detection
      algorithmic_signals.py # Higher-level pattern signals
      feature_vector.py      # Combines all features into one vector
      pattern_scorer.py      # Rule-based scoring from features
    detectors/               # Existing detectors (unchanged for now)
    coordinator.py           # Modified to use semantic features
```

### Integration Strategy

1. **Phase 1:** Build feature extraction layer as a standalone module
2. **Phase 2:** Add rule-based pattern scorer
3. **Phase 3:** Run both old detectors and new scorer, compare results
4. **Phase 4:** Gradually migrate detectors to use semantic features
5. **Phase 5:** Remove redundant old detectors

### Feature Vector Schema

```python
@dataclass
class SemanticFeatureVector:
    # Normalized AST
    normalized_loops: list[NormalizedLoop]
    normalized_comparisons: list[str]
    variable_roles: list[VariableRole]
    
    # Control flow
    loop_features: LoopFeatures
    branch_features: BranchFeatures
    recursion_features: RecursionFeatures
    
    # Data flow
    data_flow: DataFlowFeatures
    propagation: PropagationFeatures
    
    # Collection usage
    collection: CollectionFeatures
    
    # Algorithmic signals
    algorithmic: AlgorithmicSignals
    
    # Pattern scores (output)
    pattern_scores: dict[str, float]
```

---

## 10. Migration Path from Current AST Engine

### Step 1: Build Feature Extraction (No Changes to Detectors)

Create `src/ast_detection/semantic/` module with:
- `normalizer.py` — loop, comparison, expression normalization
- `control_flow.py` — loop, branch, recursion features
- `data_flow.py` — variable role, propagation features
- `collection_usage.py` — data structure usage detection
- `algorithmic_signals.py` — higher-level pattern signals
- `feature_vector.py` — combines all features

**No changes to existing detectors.**

### Step 2: Add Pattern Scorer

Create `src/ast_detection/semantic/pattern_scorer.py` with:
- Rule-based scoring for each pattern
- Confidence calibration
- Output: `dict[str, float]` (pattern → confidence)

### Step 3: Shadow Mode

Run both old detectors and new scorer in parallel:
- Old detectors: produce `DetectionResult` as before
- New scorer: produce `pattern_scores` alongside
- Log discrepancies for analysis
- No changes to production behavior

### Step 4: Gradual Migration

For each detector:
1. Verify semantic features produce same or better results
2. Add feature-based scoring as primary signal
3. Keep old detector as fallback
4. Remove old detector after sufficient validation

### Step 5: Cleanup

Remove redundant old detectors. Keep only:
- Feature extraction layer
- Pattern scorer
- Coordinator that uses scores

---

## 11. Precision/Recall Evaluation Plan

### Evaluation Corpus

Use the existing Phase-0 adversarial corpus:
- 571 seed cases
- 1025 adversarial variants
- 1596 total cases

### Evaluation Metrics

For each pattern:
- **Detection rate:** % of cases where pattern score > threshold
- **Precision:** % of high-scoring cases where pattern is correct
- **Recall:** % of correct cases where pattern is detected
- **F1:** Harmonic mean of precision and recall
- **Score calibration:** Distribution of scores for correct vs incorrect cases

### Evaluation Process

1. Run feature extraction on all 1596 cases
2. Run pattern scorer on all cases
3. Compare against ground truth labels
4. Compute per-pattern metrics
5. Identify patterns where new approach improves recall
6. Identify patterns where new approach hurts precision
7. Tune scoring thresholds to maximize F1

### Success Criteria

- Recall improvement ≥ 5% across all patterns
- Precision maintenance ≥ 99% (no degradation)
- F1 improvement ≥ 3% across all patterns
- No pattern shows precision degradation > 1%

---

## 12. What Must Remain Unchanged

| Component | Reason |
|-----------|--------|
| MatchingEngine | Already supports multiple groups, works with scores |
| Ground truth generation | Separate concern (data quality) |
| ELO system | Uses match results, not raw detection |
| Gap signals | Uses match results, not raw detection |
| Recommendations | Uses gap signals, not raw detection |
| Frontend | Displays results, doesn't affect analysis |
| Database schema | No changes needed |
| API contracts | No changes needed |

---

## 13. Risks and Failure Modes

### Risk 1: Feature Extraction Errors

**Failure mode:** Incorrectly normalizing equivalent expressions or misclassifying loop types.

**Mitigation:** Extensive unit tests for each normalization function. Cross-validate against known-equivalent code pairs.

### Risk 2: Scoring Miscalibration

**Failure mode:** Pattern scores too high (false positives) or too low (false negatives).

**Mitigation:** Conservative initial thresholds. Shadow mode testing before production deployment. Continuous monitoring of score distributions.

### Risk 3: Performance Regression

**Failure mode:** Feature extraction adds significant latency.

**Mitigation:** Feature extraction is O(n) AST walk. Benchmark against current detector latency. Cache features for repeated analysis of same code.

### Risk 4: Maintenance Burden

**Failure mode:** Feature layer becomes another collection of hard-coded heuristics.

**Mitigation:** Clear separation between feature extraction (general) and scoring (pattern-specific). Features are reusable across patterns. Scoring rules are simple and auditable.

### Risk 5: Over-Engineering

**Failure mode:** Building a complex semantic engine that solves problems PathForge doesn't have.

**Mitigation:** Start with minimal features needed to fix the two identified failures. Add features only when evidence shows they're needed. Avoid building a full program analysis framework.

---

## 14. First Experiment to Validate the Idea

### Objective

Demonstrate that semantic features can detect patterns that current detectors miss, without introducing false positives.

### Experiment Design

**Test case:** Problem 2996 (zero detections with current system)

**Code:**
```python
class Solution:
    def missingInteger(self, nums):
        i = 1
        summ = nums[0]
        while i <= len(nums)-1 and nums[i] == nums[i-1]+1:
            summ += nums[i]
            i += 1
        while summ in nums:
            summ += 1
        return summ
```

**Expected features:**
- `loop_features.has_counter_loop = True` (while with incrementing i)
- `collection_features.has_membership_test = True` (summ in nums)
- `data_flow_features.has_accumulation = True` (summ += nums[i])
- `data_flow_features.has_pointer_movement = True` (i += 1)
- `algorithmic_signals.has_two_bounds = False` (not two-pointers)
- `algorithmic_signals.has_membership_check = True`

**Expected scores:**
- `array_traversal`: 0.6-0.8 (counter loop + sequential access)
- `hash_map_lookup`: 0.3-0.5 (membership test, but no explicit dict)
- `prefix_sum`: 0.4-0.6 (accumulation pattern)

**Success criteria:**
- At least one pattern scores > 0.5 (currently all score 0)
- No pattern scores > 0.9 (conservative threshold)
- Scores are interpretable (we can explain why each score was assigned)

### Implementation

1. Build minimal feature extraction for this specific case
2. Implement rule-based scoring
3. Run on the test case
4. Verify scores are reasonable
5. Run on 10 additional cases to check for false positives
6. If successful, expand to full feature extraction

---

## 15. Conclusion

The deterministic semantic feature layer approach (Approach B) is the right architecture for PathForge because:

1. **It solves the root cause** — systemic AST blindness to equivalent implementations
2. **It preserves precision** — feature extraction is deterministic, scoring is conservative
3. **It's maintainable** — features are reusable, scoring is transparent
4. **It's fast** — O(n) AST walk, no external dependencies
5. **It's testable** — each feature can be unit tested independently
6. **It's incremental** — can be deployed in shadow mode without risk
7. **It's compatible** — works with existing MatchingEngine, ELO, and recommendation systems

The key insight is that **pattern detection should be based on what the code DOES, not how it's WRITTEN**. By extracting semantic features that are invariant to superficial code differences, we can build a detection system that's both more robust and more maintainable than the current collection of hard-coded detectors.
