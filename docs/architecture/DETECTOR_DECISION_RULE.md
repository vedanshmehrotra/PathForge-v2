# Detector Decision Rules

Version: 1.0  
Status: Frozen for Phase 3C AST System

---

## 1. Purpose

Define the exact semantic rules for interpreting detector outputs in the PathForge AST system.

This document resolves ambiguity between:

- confidence
- detection
- evidence
- classification gating

---

## 2. Detection vs Confidence

### Confidence

- Computed from evidence weights only
- Represents strength of structural signal
- Does NOT decide final classification alone

### Detected

- Boolean output of final gated decision
- Determined AFTER applying detector-specific gating rules
- NOT equivalent to `confidence > 0`

---

## 3. Detection Rule

A pattern is considered DETECTED only if:

1. At least one valid structural evidence item exists
2. Detector-specific gating conditions are satisfied
3. Confidence exceeds detector-defined threshold (if applicable)
4. No anti-signals invalidate the detection

---

## 4. Anti-Signal Priority

If any strong anti-signal is present:

- detection MUST be False
- regardless of confidence

Anti-signals override all evidence

---

## 5. DP-Specific Rules

Dynamic Programming detectors MUST follow:

### Allowed Evidence Types
- structural state transitions
- table or cache access patterns
- index dependency relationships
- recurrence-like updates
- loop-based progression over state space

### Not Allowed as Primary Signals
- semantic interpretation ("this is knapsack")
- pattern naming inference
- heuristic classification without structure

---

## 6. Memoization Rule

Memoization alone is NOT sufficient for DP detection.

Memoization MUST be combined with:

- recurrence structure OR
- state transition dependency OR
- iterative state construction

---

## 7. Confidence Interpretation

Confidence is:

- a ranking signal
- NOT a binary classifier

High confidence ≠ guaranteed detection  
Low confidence ≠ guaranteed absence

Only gating produces final decision.

---

## 8. Multi-Detector Overlap Rule

Multiple detectors MAY fire on the same AST if:

- they detect independent structural patterns

However:

- overlapping detection must not modify confidence of other detectors
- no detector suppresses another

---

## 9. System Philosophy

The AST system is:

- structural, not semantic
- evidence-driven, not heuristic
- deterministic, not probabilistic reasoning

---

## 10. Final Rule

If uncertainty exists:

DEFAULT TO NOT DETECTED