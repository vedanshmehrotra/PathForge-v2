# Ground-Truth Architecture — Ratification Sheet

**For:** subject teacher / project reviewer
**Purpose:** approve a small number of architecture rules before they are built permanently into the next version of PathForge's Ground-Truth system
**Expected time:** about 10–15 minutes
**No implementation work is requested in this review.**

---

## Section 1 — Very short context

We have completed the first **family review** of the Ground-Truth data, and your family-level decisions have been recorded and used.

The purpose of *this* next review is **not** to review individual solutions again. It is to confirm whether a few **rules** used by the Ground-Truth system are sensible before they are permanently built into the next version.

### What a "solution family" means here

> A **solution family** is a group of accepted solutions to the *same* problem that use the **same general approach**.

For example, for a problem solvable both by scanning a list and by a mathematical shortcut, the list-scanning solutions form one family and the shortcut solutions form another.

### What you already completed (for context only)

- 12 problems × 8 solutions = **96 accepted solutions**
- These grouped into **37 solution families**
- You reviewed all 37 families: **16 approved as proposed**, **20 given a corrected label**, **1 rejected**
- Result: **36 human-approved family labels**, **1 rejected family**

That review is finished and is not being reopened. This sheet is only about the seven rules below.

---

## Section 2 — Decision 1: Specific vs general labels

### The situation

Every solution family carries a label describing its approach. Some labels describe a **very specific, well-defined algorithmic approach**:

- `hash_lookup` — using a dictionary/map to look things up
- `two_pointers_opposite` — two pointers moving toward each other
- `binary_search` — repeatedly halving a search range
- `bfs_shortest_path` — breadth-first search for shortest path
- `union_find` — disjoint-set union structure
- `dp_bottom_up` — dynamic programming built up from small cases
- `dp_top_down` — dynamic programming with recursion + memoisation
- `dfs_backtracking` — depth-first search with undoing of choices

Other labels describe **broad, general patterns** that are useful but much less specific:

- `sequential_accumulation` — a value that keeps being accumulated as a loop runs
- `forward_pointer_advance` — a pointer that moves forward through a structure

### What the current design does

The **specific** labels are allowed to define an *active solution family* — meaning the system will use that family to judge new submissions.

The **broad/general** labels normally do **not** define an active family by themselves, because a general pattern can appear inside many different specific approaches.

### What we observed

Of the families you approved, **6 were approved as correct but were still not turned into active families**, because their label was one of the broad/general patterns (`forward_pointer_advance` and `sequential_accumulation`). The system refused rather than pretending a general pattern was a precise one.

### Questions

**A. Do you agree that specific algorithmic approaches should be preferred when defining an active solution family?**
- [ ] AGREE
- [ ] AGREE WITH MODIFICATION
- [ ] DISAGREE

**B. Do you agree that a broad/general pattern should NOT automatically be enough by itself to define an active family?**
- [ ] AGREE
- [ ] AGREE WITH MODIFICATION
- [ ] DISAGREE

**C. Or should there be a separate, more strictly validated mechanism for allowing a human-approved general pattern to activate?**
- [ ] AGREE
- [ ] AGREE WITH MODIFICATION
- [ ] DISAGREE

**Reason / suggested change:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 3 — Decision 2: Five basic family-difference characteristics

### The situation

When the system decides whether two solutions belong to the same family, it currently looks at **five broad characteristics**:

| # | Characteristic | Plain meaning |
|---|---|---|
| 1 | **Recursion** | Does the solution call itself? (no / once / more than once) |
| 2 | **Loop structure** | No loop / one loop / loops inside loops |
| 3 | **Container form** | How results are stored — by adding to the end, or by writing at an index |
| 4 | **Map/dictionary form** | Is a dictionary used, a fixed-size counting array, or neither? |
| 5 | **Collection iteration** | Is a collection being stepped through, and how |

These are **not** algorithm names. They are simply broad, obvious characteristics used to tell different implementation approaches apart.

### Question

**Do these five characteristics seem reasonable as general information for distinguishing solution families?**
- [ ] APPROVE
- [ ] APPROVE WITH CHANGES
- [ ] REJECT / NEED MORE INFORMATION

**Comments:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 4 — Decision 3: Brute force

### Your earlier concern

You raised the point that **"brute force" should not simply mean "the code contains loops."**

### What the analysis found

We checked this against the 37 reviewed families:

- **12 families** contain loops inside loops
- Of those 12, only **4** were judged by you to be genuine brute force
- The other **8** were legitimate, more specific approaches:

| Family | Your label | Characteristics |
|---|---|---|
| LC 102 — family 1 | `bfs_shortest_path` | BFS, accepted |
| LC 125 — family 1 | `two_pointers_opposite` | accepted |
| LC 209 — family 1 | `sequential_accumulation` + `sliding_window` | accepted |
| LC 209 — family 3 | `sequential_accumulation` | approved as correct |
| LC 547 — family 1 | `bfs_shortest_path` | approved as correct |
| LC 547 — family 3 | `union_find` | accepted |
| LC 560 — family 4 | `sequential_accumulation` | approved as correct |
| LC 46 — family 1 | `iterative_insertion` | approved as correct |

So **"nested loop" is not a reliable definition of brute force** — two thirds of the nested-loop families were legitimate specific approaches.

### Current recommendation

> **Keep `brute_force` as a family-level descriptive label for now, but do NOT make it a runtime detection concept yet.**

A descriptive label is documentation for humans. A runtime concept would make the system automatically judge new submissions as "brute force", which we are not yet confident it can do accurately.

### Question

**Do you agree that `brute_force` should remain a descriptive label until a more reliable definition can be established?**
- [ ] YES
- [ ] NO
- [ ] NEEDS MODIFICATION

**Comments:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 5 — Decision 4: Excluded rules

### The situation

Some problem-level labels carry an **exclusion rule** — a statement such as "this approach is *not* the intended solution".

Earlier, when one problem had several different solution families, an exclusion rule attached to one family could be **copied automatically onto the other families of the same problem**. This caused valid alternative approaches to be flagged as *contradictory*, even though the alternative approach was perfectly acceptable for that problem.

### What happened after the review

Removing those automatically-copied exclusions made the previous **4 contradictions disappear** (contradicted cases went from **4 → 0**). We consider this a correction, not a loss of strictness — the flagged solutions were legitimate alternative approaches.

### Question

**Should an exclusion rule belong to the specific solution family that was reviewed, rather than automatically being copied to every solution family of the same problem?**
- [ ] YES
- [ ] NO
- [ ] NEEDS MODIFICATION

**Comments:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 6 — Decision 5: Families with no recognised signals ("zero-evidence")

### The situation

Some solutions currently produce **no recognisable algorithmic signals** — the analysis cannot see any pattern it knows. The system groups these together under the state **`ZERO_EVIDENCE`**.

### The problem your review exposed

One family was **rejected** because it mixed two genuinely different approaches:

- a solution comparing letter counts with a **counting structure**
- a solution comparing sorted versions of both strings

Both produced no recognisable signals, so they were grouped together **only because both were "unknown"**. This shows that *absence of signals does not prove that two solutions use the same approach*.

Your recorded reason was: *"the sheet itself flags zero-evidence members alongside a Counter-equality member; family coherence can't be confirmed from what's given, so it shouldn't be reviewed as one approved family."* We have kept this family rejected.

### Current safe behaviour (already in force)

- `ZERO_EVIDENCE` is **never labelled**
- **never** used to judge submissions
- **never** used as a comparison control
- It simply records "we could not classify this"

### Question

**Which approach should we take?**
- [ ] **Option A** — Keep `ZERO_EVIDENCE` as a refused/unclassified state. Do not use it to assign algorithm labels. Accept that it may temporarily contain different approaches.
- [ ] **Option B** — Try to further split `ZERO_EVIDENCE` families using other available structural information.
- [ ] **Option C** — Other suggestion (describe below).

**Comments / other suggestion:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 7 — Decision 6: Human-approved labels that are still too general

### The situation

This is related to Decision 1, but it is listed separately because the review produced a concrete example.

The review identified **6 families where your label was accepted as correct, but the system still refused to build an active family**, because the label was considered too general to identify reliably on its own.

The labels involved were:

- `forward_pointer_advance` (2 families)
- `sequential_accumulation` (4 families)

### Why the system refuses

A general pattern like "a value is accumulated in a loop" also appears inside *other* approaches — for example inside a brute-force scan or a sliding window. If the system accepted it as an active family, it would risk confirming submissions for the wrong reason.

### The trade-off

This is a balance between **trusting your label** and **avoiding over-broad confirmation rules**:

- **Keep strict** → fewer wrong confirmations, but some correctly-labelled families stay unused.
- **Allow a special reviewed group** → better coverage, but those families would need extra validation to stay safe.

### Question

**Should the current rule remain strict, meaning a human-approved general label can still remain unused if the system cannot distinguish it reliably?**
- [ ] KEEP STRICT RULE
- [ ] ALLOW A SPECIAL REVIEWED GENERIC GROUP
- [ ] OTHER (describe below)

**Comments:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 8 — Decision 7: Ground-Truth versioning and approval principles

### The situation

Before the Ground-Truth data is stored permanently, a few organisational corrections were identified so that versions, approvals, validation status and origin are represented consistently.

These are **principles**, not database details. You are not being asked to approve table names or technical schema.

### The intended principles

1. **Immutable versions** — an approved Ground-Truth version is never edited in place. Changes create a new version.
2. **Explicit approval before activation** — generated Ground-Truth never becomes active on its own; a human approval step is required.
3. **Separate validation from approval** — "did it pass the checks?" and "did a human approve it?" are two different statuses and are recorded separately.
4. **Preserved origin and validation records** — for every version we keep where the solutions came from and which checks it passed.
5. **No silent replacement** — a new version never quietly overwrites an older approved one; the older version remains recoverable.

### Question

**Do you approve these principles for the permanent Ground-Truth system?**
- [ ] APPROVE
- [ ] APPROVE WITH CHANGES
- [ ] REJECT

**Comments:**

```
______________________________________________________________________

______________________________________________________________________
```

---

## Section 9 — Final approval summary

| # | Decision | Your decision | Comments |
|---|---|---|---|
| 1 | Specific vs general labels | | |
| 2 | Five family-difference characteristics | | |
| 3 | Brute-force policy | | |
| 4 | Excluded-rule scope | | |
| 5 | Zero-evidence policy | | |
| 6 | General-label activation rule | | |
| 7 | Ground-Truth versioning / approval principles | | |

> **These decisions are architecture guidance for the next Ground-Truth version. They do not require implementation during this review.**

**Reviewer name:** ____________________________

**Date:** ____________________________

**Signature (optional):** ____________________________

---

### Reviewer notes

Any additional comments, or items you would prefer to revisit before these rules are fixed:

```
______________________________________________________________________

______________________________________________________________________

______________________________________________________________________
```

---

*Prepared for architecture ratification only. No production behaviour, detectors, matching logic, runtime vocabulary or existing Ground-Truth rows were changed in preparing this document.*
