# PathForge Research Contribution / Novelty Test

**Date**: 2026-08-27
**Commit**: b88cab4

---

## 1. What Is Technically Novel Compared With Existing AST/Code-Pattern Learner Modeling?

### The Layered Decomposition (Facts → Techniques → Strategies)

**This is the strongest novel element.** PathForge decomposes code analysis into three explicit layers:

1. **Structural Facts** (~25+ types): Deterministic, syntax-normalized AST observations (e.g., `while_loop_comparison`, `opposite_direction_updates`, `midpoint_calculation`, `state_restoration`). These are *observations*, not labels.

2. **Techniques** (9 types): Reusable computational primitives composed from facts (e.g., `bidirectional_index_scan` requires `while_loop_comparison` + `opposite_direction_updates`; `recursive_branching` requires `self_recursive_call` + `recursive_call_in_conditional`).

3. **Strategies** (9 types): Higher-level algorithmic patterns composed from techniques with absence constraints (e.g., `two_pointers_opposite` requires `bidirectional_index_scan` AND `while_loop_comparison` AND `opposite_direction_updates` AND NOT `midpoint_calculation`).

**What makes this different from existing work:**

| Aspect | PathForge | Code-DKT (Shi 2022) | Hoq et al. (2025) | srcML-DKT (2025) |
|--------|-----------|---------------------|-------------------|-------------------|
| Pattern origin | Hand-crafted CS education theory | Learned from data | Learned from data (VAE+K-means) | Learned from srcML |
| Interpretability | Full evidence chain (fact→technique→strategy) | Attention weights (opaque) | Cluster centroids (semi-opaque) | Attention weights (opaque) |
| Naming independence | Partial (facts use some names) | Uses token embeddings | Normalizes identifiers | Uses srcML tokens |
| Absence constraints | Explicit (e.g., NOT midpoint for two-pointers) | None | None | None |
| Authority system | Tiered (bootstrap/LLM/editorial/observed) | None | None | None |

**The absence constraint mechanism is genuinely novel.** Existing AST pattern detectors check for *presence* of features. PathForge's strategy layer also checks for *absence* of conflicting features (e.g., "two_pointers_opposite" must NOT have `midpoint_calculation` — because midpoint + opposite updates = binary search, not two pointers). This disambiguation mechanism has no direct equivalent in the literature.

### Confidence Separation (Presence vs. Centrality)

PathForge separates two orthogonal confidence dimensions:
- **presence_confidence**: How likely is this technique present? (0.0–1.0)
- **centrality**: How central is this technique to the algorithm? (0.0–1.0)

A technique can be present but not central (e.g., `sequential_accumulation` in a sliding window implementation). This distinction is not made in any existing code analysis system for education.

### Authority-Gated Matching

Solution groups have explicit authority tiers (`bootstrap`, `llm_proposed`, `externally_listed`, `structurally_observed`, `editorial`). Lower-authority contradictions are downgraded to `UNRESOLVED` rather than `CONTRADICTED`. This prevents unreliable ground truth from triggering incorrect ELO updates. No existing educational code analysis system implements this.

---

## 2. What Is Methodologically Novel?

**The research methodology itself is not novel.** PathForge uses:
- AST parsing (standard since the 1970s)
- Pattern matching on AST structures (standard in program analysis)
- Rule-based detection (standard in static analysis)
- Confidence scoring (standard in classification)

**The methodological contribution, if any, is the *evaluation framework***: per-concept P/R/F1 against a predefined vocabulary, robustness testing across semantically equivalent variants, and error localization into failure layers. This evaluation methodology is more rigorous than what most educational code analysis papers report, but it is not itself a research contribution — it is good engineering practice.

---

## 3. What Problem Does PathForge Solve That Existing Approaches Do Not Solve Adequately?

### The Interpretability Gap

Existing AST-based learner modeling (Code-DKT, Hoq et al., srcML-DKT) uses deep learning to extract features from code. These features are:
- **Opaque**: Attention weights tell you which subtree matters, not *why*
- **Data-dependent**: Patterns are discovered from training data, not from CS education theory
- **Not composable**: A detected pattern doesn't tell you which sub-patterns compose it

PathForge provides:
- **Full evidence chain**: "This is two_pointers_opposite because: (1) while_loop_comparison on left/right, (2) opposite_direction_updates with left+=1 and right-=1, (3) no midpoint_calculation"
- **Theory-grounded vocabulary**: Patterns defined by CS educators, not discovered by clustering
- **Composable evidence**: Techniques compose from facts; strategies compose from techniques

### The Ground Truth Problem

Existing approaches either:
- Use correctness as the only label (Code-DKT) — doesn't capture *what* the student knows
- Use problem tags as KC labels (many ITS) — doesn't capture *how* the student solved it
- Use LLM-generated labels (some recent work) — introduces LLM bias

PathForge attempts to solve this by detecting concepts from the *code itself*, independent of problem tags or correctness. This is a genuine conceptual contribution to the research question, even if the current implementation doesn't fully deliver on it.

---

## 4. What Is the Primary Nature of the Contribution?

**The contribution is primarily a new learner-modeling signal** — specifically, a structured, interpretable representation of algorithmic concepts detected from student code.

It is NOT:
- A new representation (AST is standard; the fact/technique/strategy vocabulary is new but the representation format is not)
- A new matching method (set intersection with absence constraints is simple)
- A new uncertainty framework (confidence scores are hand-tuned, not calibrated)
- A new recommendation mechanism (ELO-based recommendation is standard)

It IS:
- A new *vocabulary* of algorithmic concepts defined by CS education theory
- A new *compositional structure* for detecting those concepts (facts→techniques→strategies)
- A new *evidence model* that provides interpretable chains from code structure to concept labels

---

## 5. The 3–5 Closest Research Papers

### Paper 1: Hoq et al. (2025) — "Pattern-based Knowledge Component Extraction from Student Code Using Representation Learning"

**Published**: EDM 2025 / arXiv 2508.09281
**Citations**: 5

| Aspect | Hoq et al. (2025) | PathForge |
|--------|-------------------|-----------|
| Input | Java code submissions (47,764 from CodeWorkout) | Python code submissions (81 synthetic) |
| Representation | AST subtree sequences → VAE latent space | AST → structural facts → techniques → strategies |
| Inference | VAE encoder + K-means clustering | Hand-crafted rule matching |
| Learner model | DKT with pattern-based KCs | ELO + topic profiles + gap signals |
| Evaluation | Learning curves + DKT AUC | Per-concept P/R/F1 + robustness |
| Target outcome | Predict student future success | Identify algorithmic concepts in code |
| Limitations | Opaque clusters, no absence constraints, data-dependent | Brittle rules, low robustness, small dataset |

**Key difference**: Hoq et al. learn patterns from data; PathForge defines patterns from theory. Hoq et al. scale to 47K submissions; PathForge currently handles 81. Hoq et al. optimize for prediction accuracy; PathForge optimizes for interpretability.

### Paper 2: Shi et al. (2022) — "Code-DKT: A Code-based Knowledge Tracing Model for Programming Tasks"

**Published**: EDM 2022
**Citations**: 72

| Aspect | Code-DKT (2022) | PathForge |
|--------|-----------------|-----------|
| Input | Java code (CodeWorkout, ~47K submissions) | Python code (81 synthetic) |
| Representation | AST → attention-weighted token sequences | AST → structural facts → techniques → strategies |
| Inference | Transformer-based attention mechanism | Hand-crafted rule matching |
| Learner model | DKT (RNN-based) | ELO + topic profiles |
| Evaluation | AUC for correctness prediction | Per-concept P/R/F1 |
| Target outcome | Predict correct/incorrect | Identify algorithmic concepts |
| Limitations | No concept-level explanation, opaque features | Brittle rules, low coverage |

**Key difference**: Code-DKT predicts *whether* a student will succeed; PathForge attempts to identify *what* the student knows. These are complementary, not competing, objectives.

### Paper 3: Pankiewicz et al. (2025) — "srcML-DKT: Enhancing Deep Knowledge Tracing with Robust Code Representations"

**Published**: EDM 2025
**Citations**: 5

| Aspect | srcML-DKT (2025) | PathForge |
|--------|-------------------|-----------|
| Input | Java code (CodeWorkout) | Python code (81 synthetic) |
| Representation | srcML XML → token sequences | AST → facts → techniques → strategies |
| Inference | Transformer attention | Hand-crafted rules |
| Learner model | DKT with srcML features | ELO + topic profiles |
| Evaluation | AUC for prediction | Per-concept P/R/F1 |
| Limitations | Language-dependent (srcML), opaque | Language-specific (Python AST), brittle |

**Key difference**: srcML-DKT improves representation robustness over Code-DKT; PathForge improves interpretability. Both face the same fundamental challenge: representing code in a way that captures algorithmic intent.

### Paper 4: Hoq et al. (2025b) — "Automated Identification of Logical Errors in Programs"

**Published**: EDM 2025
**Citations**: 20

| Aspect | Hoq et al. (2025b) | PathForge |
|--------|-------------------|-----------|
| Input | Java code (CodeWorkout) | Python code (81 synthetic) |
| Representation | SANN (Subtree-based Attention Neural Network) | Structural facts from AST |
| Inference | Attention-based neural network | Hand-crafted rules |
| Target | Detect logical errors in student code | Detect algorithmic concepts |
| Limitations | Requires training data, error-type taxonomy is limited | Rule-based, doesn't detect errors |

**Key difference**: This paper focuses on *error detection*; PathForge focuses on *concept detection*. They address different questions but use similar AST-based representations.

### Paper 5: Rivers et al. (2016) — "Automating Cross-Fertilization of Knowledge Components"

**Published**: 2016
**Citations**: 35

| Aspect | Rivers et al. (2016) | PathForge |
|--------|---------------------|-----------|
| Input | Java code (CodeWorkout) | Python code (81 synthetic) |
| Representation | AST node types as KCs | Structural facts → techniques → strategies |
| Inference | Manual KC mapping + clustering | Hand-crafted rules |
| Learner model | Bayesian Knowledge Tracing | ELO + topic profiles |
| Evaluation | Learning curve alignment | Per-concept P/R/F1 |
| Limitations | Manual KC specification, limited scalability | Rule-based, limited scalability |

**Key difference**: Rivers et al. manually specify KCs and use AST node types as proxies; PathForge automatically detects concepts from code structure. PathForge's vocabulary is more semantically meaningful than raw AST node types.

---

## 6. The Clearest Defensible Research Gap

**The gap is: "Can a theory-grounded, compositional, rule-based code analysis system identify algorithmic concepts in student code with sufficient accuracy and robustness to serve as a learner-modeling signal?"**

This gap is defensible because:

1. **No existing system combines theory-grounded pattern definition with compositional detection.** Code-DKT and Hoq et al. learn patterns from data. Rivers et al. use manual KC mapping. PathForge attempts to bridge this by defining patterns from CS education theory AND detecting them compositionally from code structure.

2. **No existing system provides full evidence chains for concept detection.** When Code-DKT assigns a KC, you see an attention weight. When PathForge detects `two_pointers_opposite`, you see: "while_loop_comparison on [left, right] + opposite_direction_updates with left incrementing and right decrementing + no midpoint_calculation." This interpretability is valuable for educational settings where teachers need to understand *why* a system thinks a student knows something.

3. **No existing system implements absence constraints for algorithmic disambiguation.** The insight that "two pointers is NOT binary search because there's no midpoint" is pedagogically meaningful and technically useful for reducing false positives.

---

## 7. The Strongest Argument AGAINST PathForge Being a Sufficiently Novel Research Contribution

**The strongest argument is: PathForge is an engineering project that has not demonstrated empirical superiority over existing approaches on any standard evaluation metric.**

Specifically:

1. **No comparison with baselines.** PathForge has never been compared against Code-DKT, Hoq et al., or any existing system on the same dataset. Without this comparison, it is impossible to claim that the novel architecture produces better results.

2. **The dataset is synthetic and tiny.** 81 template submissions vs. 47,764 real student submissions. The evaluation does not reflect real-world conditions.

3. **The rule-based approach has fundamental limitations.** The robustness test shows 35.7% stability rate — the system changes its answer when given semantically equivalent code. This is worse than no system at all for research purposes.

4. **The shadow system (the theoretically novel part) barely works.** Macro F1 = 0.079. The compositional fact→technique→strategy architecture, which is the primary novel contribution, currently detects almost nothing.

5. **The vocabulary is not validated.** The 42 concepts, 9 techniques, and 9 strategies were defined by the developers, not validated against expert consensus or student learning data. Are these the right concepts? At the right granularity? We don't know.

6. **The full pipeline (learner modeling + recommendation) has never been evaluated.** The ELO system, topic profiles, and gap signals have not been tested against any baseline.

**In summary: PathForge proposes a novel architecture but has not produced evidence that the architecture works better than existing approaches, or even works adequately on its own terms.**

---

## 8. Is the Project Better Framed As...

### **C: Research Prototype Requiring a Stronger Experimental Question**

**Reasoning:**

- **(A) Research contribution**: Not yet. The novelty is real but undemonstrated. No comparison with baselines, no real-world evaluation, no validation of the vocabulary.

- **(B) Engineering/tool contribution**: Partially. The implementation is substantial (36 detectors, 9 techniques, 9 strategies, full pipeline). But the engineering has critical robustness flaws (35.7% stability) that prevent it from being a reliable tool.

- **(C) Research prototype requiring a stronger experimental question**: **Yes.** The architecture is sound in principle. The research idea (theory-grounded compositional code analysis for learner modeling) is defensible. But the experimental question needs to be sharpened and the evaluation needs to be rigorous:
  - Compare against Code-DKT / Hoq et al. on the same dataset
  - Test on real student submissions, not synthetic templates
  - Validate the vocabulary against expert judgments
  - Demonstrate that interpretability provides measurable benefit (e.g., teacher trust, error diagnosis accuracy)

- **(D) Insufficiently novel**: No. The compositional fact→technique→strategy architecture with absence constraints and authority gating is genuinely novel. The problem is demonstration, not invention.

---

## 9. Summary: Honest Novelty Assessment

| Dimension | Assessment |
|-----------|------------|
| **Technical novelty** | Moderate. The layered decomposition + absence constraints + authority gating are genuinely new combinations. Individual components (AST analysis, rule-based detection) are not new. |
| **Methodological novelty** | Low. Standard evaluation metrics, no novel methodology. |
| **Problem formulation novelty** | Moderate-High. The research question ("can code analysis identify algorithmic concepts?") is important and underexplored with interpretable methods. |
| **Empirical contribution** | Very Low. 81 synthetic submissions, no baseline comparison, no real-world evaluation. |
| **Practical utility** | Low. The system is too brittle (35.7% robustness) and too narrow (shadow covers ~11% of concepts) to be useful in practice. |
| **Theoretical contribution** | Low. No formal model, no proofs, no theoretical framework beyond the vocabulary definitions. |

**Bottom line:** PathForge has a genuine but unproven novel idea. The compositional, interpretable, theory-grounded approach to code analysis for learner modeling fills a real gap in the literature. But the current implementation has not demonstrated that this approach actually works. The project is best framed as a **research prototype that needs rigorous empirical validation** before it can be considered a research contribution.

**To become a publishable research contribution, PathForge would need:**
1. Evaluation on real student submissions (1,000+ from CodeWorkout or similar)
2. Direct comparison with Code-DKT and Hoq et al. on the same dataset
3. Expert validation of the concept vocabulary
4. Demonstration that interpretability provides measurable benefit (user study with teachers)
5. Robustness improvement to >80% stability rate
6. Formal description of the fact→technique→strategy compositional model

Without these, the project remains an interesting engineering prototype with a promising but unvalidated research direction.
