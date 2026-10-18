# Approach-family contract — architectural review draft

Status: approved for the bounded local implementation; no authority promotion
or changes to existing stored ground truth are authorized.
Release target: a reviewed core set, with observational analysis outside it.

## Meaning

- A technique is an observed operation; it is not necessarily a strategy.
- An approach is one coherent way to solve a problem. Its reviewed required
  components are conjunctive; optional components are not prerequisites.
- Alternative approaches are explicit choices. Satisfying one does not require
  the components of the others. Preserve existing explicit `ONE_OF` decisions.
- A flat list of labels does not establish whether its items are complementary
  or alternative. Taxonomy membership cannot establish that relationship.
- A reviewed approach is not necessarily detectable by the current engine.
  Record coverage limitations separately from ground-truth validity.
- Pattern alignment does not establish functional correctness or optimality.
- Brute force is not inherently an unsuitable approach. Exhaustive enumeration
  may be appropriate or output-size optimal; suitability depends on the problem,
  constraints and required output, not the technique's name. The supported core
  need not cover every valid implementation. Missing coverage is not a negative
  judgment of solution quality, and the detector must not invent optimality.

## Proposed behavior

1. New generation requests explicit proposed approaches and their component
   patterns. Preserve a single explicit approach as well as multiple approaches;
   do not split its components into alternatives by technique category.
2. Generated expectations remain `llm_proposed`. Neither a model confidence,
   successful schema validation, nor this contract confers canonical authority.
3. Existing rows are not rewritten, regenerated, relabeled or automatically
   approved. Flat or inferred relationships remain diagnostic and require review
   before they support trustworthy approach-specific feedback.
4. Matching exposes per-approach observed and unobserved requirements. When an
   explicitly accepted alternative fully matches, other alternatives do not
   create a submission gap. If none matches, show the per-approach comparison;
   do not infer the user's intended approach or call every unobserved technique
   a skill deficiency.
5. The API retains existing fields and adds approach structure, provenance,
   comparison results and coverage/review limitations for presentation.
6. The main analysis view distinguishes observed techniques, reviewed approach
   alignment and inconclusive comparisons. It does not flatten alternative
   families into a universal checklist. Canonical strategy conclusions and
   product authority remain separate; Shadow stays observational by default.
7. Outside the reviewed core, accept observational analysis and explain the
   limits of problem-specific comparison. Do not fabricate an expected strategy
   for a valid solution outside the vocabulary.

## Frozen acceptance examples

| Example | Independently justified expectation |
| --- | --- |
| Fixed-size maximum-sum window | Incoming `nums[i]` and outgoing `nums[i-k]` maintain the same accumulator; existing window support must survive. |
| Classic sequence binary search | Ordered `arr[midpoint]` decisions narrow the same interval to `midpoint +/- 1`; existing support must survive. |
| Functional DSU | Representative traversal, path compression and linking representative roots share the parent structure; existing support must survive. |
| Two Sum with a dictionary | Complement lookup is technique evidence; it need not be a conclusion-eligible canonical strategy. |
| Prefix accumulation plus dictionary lookup in one explicit approach | Components remain together. Detecting one component is not a complete approach match. |
| Two explicitly accepted alternatives, one fully matched | Full alignment with that alternative; zero missing requirements from the unused alternative. |
| No alternative fully matched | Per-approach evidence limitations; no invented intent or functional-correctness verdict. |
| Remove Outermost Parentheses using nesting depth | No fixed-window claim; lack of vocabulary coverage must not imply an incorrect solution. |
| Legacy flat labels or incomplete family metadata | No claim that the labels establish a reviewed, exhaustive set of alternatives. |

Source examples for existing supported detectors are read directly from
`pathforge/ast_analysis/shadow/tests/evaluation_corpus.py`; corpus labels are not
the basis of these expectations. Contract probes use local connection doubles,
mocked generation output and real analysis/Shadow engines. Submitted programs
are parsed, never executed.

## Approved architectural decision

The user approved explicit approach definitions for newly generated expectations,
including conservative treatment of ambiguous cached labels. Historical cached
comparisons remain compatible and diagnostic. This is a deliberate contract
change rather than an isolated detector repair.

Product consequences need a separate reviewed policy: this draft does not
authorize changing legacy scoring, canonical authority, flag defaults, stored
ground truth, migrations or production state. The first implementation should
preserve those boundaries and surface honest comparison limitations.

## Verification and stopping conditions

Freeze source-based expectations before engine execution. Verify builder and
resolver behavior, real matching and Shadow output, API serialization, and the
rendered UI with mocked transport. Use no configured database or external LLM.
Run focused tests before affected regressions. Allow at most two corrections to
the same acceptance failure; stop on repeated failure, scope expansion or a new
semantic decision. Report executed checks separately from historical evidence.
