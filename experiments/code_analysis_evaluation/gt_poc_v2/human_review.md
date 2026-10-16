# Ground-Truth POC V2 — Human Review (Round 1)

- **reviewer:** external human reviewer (subject teacher)
- **mode:** blind_family_review (analyzer detections were NOT shown)
- **status:** COMPLETED
- **scope:** every family produced by the V2 POC grouping stage (37 families, 96 solutions, 12 problems)

## Summary

- reviewed families: **37**
- APPROVED: **16**
- CORRECTED LABEL: **20**
- REJECTED: **1**

## Source provenance

| artifact | sha256 | role |
|---|---|---|
| `PathForge_V2_Review_Decisions-2.pdf` | `cc689465bc41844a433e8e8b2b676e1381149dc15d99a35d886a3084fb9eba5b` | authoritative reviewer decisions and remarks (raw teacher artifact) |
| `pathforge_v2_solutions.pdf` | `71b64b504ff147ff12547ded626270cb567e4c3620e95422039174e4e1e08ffb` | the blind review sheet that was handed to the reviewer (one reference implementation per family) |
| `human_review_source.txt` | `3d800508c27333321896e71a00837f309a4dc56a780db472d92e1f6f748e4391` | mechanical pdftotext -layout extraction of decisions_pdf (traceability only) |
| `human_review_solutions_source.txt` | `887f01539ed7bb3a8cca8f549841fa5ce197014ecfed713bec28bcfeb7707a1b` | mechanical pdftotext extraction of solutions_pdf; carries per-family decision docstrings used for verification |

Raw reviewer PDFs are never modified. `human_review_source.txt` / `human_review_solutions_source.txt` are mechanical `pdftotext` extractions used only for verification.

## Transcript verification

- passed: **True**
- failed checks: none

| check | passed | detail |
|---|---|---|
| `decision_count` | yes | 37 decisions for 37 families |
| `unique_family_keys` | yes | 37 unique of 37 |
| `coverage_bijective` | yes | unreviewed=[] unknown=[] |
| `tally_matches_summary` | yes | transcript={'APPROVED': 16, 'CORRECTED_LABEL': 20, 'REJECTED': 1} summary={'reviewed_families': 37, 'approved': 16, 'corrected_label': 20, 'rejected': 1} |
| `reviewer_reason_recorded` | yes | every decision carries a reviewer reason |
| `source_ref_recorded` | yes | every decision carries a source reference |
| `review_status_recorded` | yes | every decision carries a review status |
| `label_terms_recorded` | yes | every non-rejected decision has label terms |
| `no_vocabulary_invention` | yes | label terms are non-empty identifiers |
| `source_digests_not_mismatched` | yes | decisions_pdf=verified; solutions_pdf=verified; extracted_decisions_txt=verified; extracted_solutions_txt=verified |
| `extraction_family_keys_match` | yes | decisions pdf mentions 37 family keys |
| `extraction_summary_match` | yes | summary line ['16', '20', '1'] vs {'reviewed_families': 37, 'approved': 16, 'corrected_label': 20, 'rejected': 1} |
| `extraction_decisions_match` | yes | parsed 37 per-family decisions from the reviewer sheet; mismatches=[] |
| `extraction_labels_match` | yes | label mismatches between reviewer sheet and transcript: [] |

## Reviewer remarks

- Completed review of every family in the simplified V2 review sheet. Judged solely on algorithmic approach vs. proposed label, per the review guide.
- The review guide explicitly allows 'brute_force' as a corrected label (its own LC1 fam2/fam3 example). A few other families needed a descriptive label not in the fixed vocabulary list (e.g. sort_and_rebuild, recursive_merge, iterative_insertion, dp_top_down, recursive_dfs_by_depth, clean_and_compare_reverse, recursive_dfs_traversal). These follow the same plain-English, approach-describing style as the provided vocabulary and are flagged for the team's discretion.
- lc242_fam2 flagged REJECTED: the sheet's own description says the family 'contains zero-evidence members' alongside one Counter-equality member. Since coherence of the family (whether all members share one approach) cannot be verified from what is given, this is the one case matching the REJECTED criterion -- not because the visible code is wrong, but because the family's coherence is unconfirmed.

## Family-level decisions

| family | n | decision | human label | approved label terms | before (POC proposed) | after (divergence state) | vocabulary gap |
|---|---|---|---|---|---|---|---|
| `lc1_fam1` | 3 | APPROVED | hash_lookup | hash_lookup | hash_lookup | `LABEL_OK` | — |
| `lc1_fam2` | 2 | CORRECTED_LABEL | brute_force | brute_force | _(no label)_ | `ZERO_EVIDENCE` | brute_force |
| `lc1_fam3` | 1 | CORRECTED_LABEL | brute_force | brute_force | _(no label)_ | `LABEL_UNEXPRESSIBLE` | brute_force |
| `lc1_fam4` | 2 | CORRECTED_LABEL | two_pointers_opposite | two_pointers_opposite | _(no label)_ | `LABEL_OK` | — |
| `lc21_fam1` | 1 | APPROVED | forward_pointer_advance | forward_pointer_advance | forward_pointer_advance | `LABEL_GENERIC` | — |
| `lc21_fam2` | 2 | CORRECTED_LABEL | sort_and_rebuild | sort_and_rebuild | _(no label)_ | `LABEL_UNEXPRESSIBLE` | sort_and_rebuild |
| `lc21_fam3` | 2 | APPROVED | forward_pointer_advance | forward_pointer_advance | forward_pointer_advance | `LABEL_GENERIC` | — |
| `lc21_fam4` | 3 | CORRECTED_LABEL | recursive_merge | recursive_merge | _(no label)_ | `LABEL_UNEXPRESSIBLE` | recursive_merge |
| `lc46_fam1` | 3 | CORRECTED_LABEL | iterative_insertion | iterative_insertion | _(no label)_ | `ZERO_EVIDENCE` | iterative_insertion |
| `lc46_fam2` | 2 | APPROVED | dfs_backtracking | dfs_backtracking | dfs_backtracking | `LABEL_OK` | — |
| `lc46_fam3` | 3 | APPROVED | dfs_backtracking | dfs_backtracking | dfs_backtracking | `LABEL_OK` | — |
| `lc70_fam1` | 3 | APPROVED | dp_bottom_up | dp_bottom_up | dp_bottom_up | `LABEL_OK` | — |
| `lc70_fam2` | 3 | CORRECTED_LABEL | dp_top_down | dp_top_down | _(no label)_ | `LABEL_OK` | — |
| `lc70_fam3` | 2 | CORRECTED_LABEL | dp_bottom_up | dp_bottom_up | _(no label)_ | `ZERO_EVIDENCE` | — |
| `lc102_fam1` | 4 | APPROVED | bfs_shortest_path | bfs_shortest_path | bfs_shortest_path | `LABEL_OK` | — |
| `lc102_fam2` | 4 | CORRECTED_LABEL | recursive_dfs_by_depth | recursive_dfs_by_depth | _(no label)_ | `LABEL_UNEXPRESSIBLE` | recursive_dfs_by_depth |
| `lc125_fam1` | 3 | APPROVED | two_pointers_opposite | two_pointers_opposite | two_pointers_opposite | `LABEL_OK` | — |
| `lc125_fam2` | 2 | CORRECTED_LABEL | clean_and_compare_reverse | clean_and_compare_reverse | _(no label)_ | `ZERO_EVIDENCE` | clean_and_compare_reverse |
| `lc125_fam3` | 3 | CORRECTED_LABEL | two_pointers_opposite | two_pointers_opposite | _(no label)_ | `LABEL_UNEXPRESSIBLE` | — |
| `lc209_fam1` | 4 | APPROVED | sequential_accumulation + sliding_window | sequential_accumulation, sliding_window | sequential_accumulation, sliding_window | `LABEL_OK` | — |
| `lc209_fam2` | 2 | CORRECTED_LABEL | brute_force | brute_force | _(no label)_ | `LABEL_UNEXPRESSIBLE` | brute_force |
| `lc209_fam3` | 2 | CORRECTED_LABEL | sequential_accumulation | sequential_accumulation | _(no label)_ | `LABEL_GENERIC` | — |
| `lc242_fam1` | 3 | APPROVED | frequency_counting | frequency_counting | frequency_counting | `LABEL_OK` | — |
| `lc242_fam2` | 2 | REJECTED | _(rejected)_ | — | _(no label)_ | `ZERO_EVIDENCE` | — |
| `lc242_fam3` | 3 | APPROVED | frequency_counting | frequency_counting | frequency_counting | `LABEL_OK` | — |
| `lc547_fam1` | 2 | CORRECTED_LABEL | bfs_shortest_path | bfs_shortest_path | _(no label)_ | `LABEL_UNEXPRESSIBLE` | — |
| `lc547_fam2` | 3 | CORRECTED_LABEL | recursive_dfs_traversal | recursive_dfs_traversal | _(no label)_ | `LABEL_UNEXPRESSIBLE` | recursive_dfs_traversal |
| `lc547_fam3` | 3 | APPROVED | union_find | union_find | union_find | `LABEL_OK` | — |
| `lc560_fam1` | 2 | CORRECTED_LABEL | brute_force | brute_force | _(no label)_ | `LABEL_UNEXPRESSIBLE` | brute_force |
| `lc560_fam2` | 2 | APPROVED | frequency_counting + sequential_accumulation | frequency_counting, sequential_accumulation | frequency_counting, sequential_accumulation | `LABEL_OK` | — |
| `lc560_fam3` | 2 | CORRECTED_LABEL | frequency_counting + sequential_accumulation | frequency_counting, sequential_accumulation | _(no label)_ | `LABEL_PARTIAL` | — |
| `lc560_fam4` | 2 | CORRECTED_LABEL | sequential_accumulation | sequential_accumulation | _(no label)_ | `LABEL_GENERIC` | — |
| `lc704_fam1` | 4 | APPROVED | binary_search | binary_search | binary_search | `LABEL_OK` | — |
| `lc704_fam2` | 1 | CORRECTED_LABEL | binary_search | binary_search | _(no label)_ | `ZERO_EVIDENCE` | — |
| `lc704_fam3` | 3 | CORRECTED_LABEL | binary_search | binary_search | _(no label)_ | `LABEL_UNEXPRESSIBLE` | — |
| `lc3236_fam1` | 7 | APPROVED | sequential_accumulation | sequential_accumulation | sequential_accumulation | `LABEL_GENERIC` | — |
| `lc3236_fam2` | 1 | APPROVED | sequential_accumulation | sequential_accumulation | sequential_accumulation | `LABEL_GENERIC` | — |

## Vocabulary gaps (human label terms the frozen taxonomy does not register)

- `brute_force` — 4 family/families: lc1_fam2, lc1_fam3, lc209_fam2, lc560_fam1
- `clean_and_compare_reverse` — 1 family/families: lc125_fam2
- `iterative_insertion` — 1 family/families: lc46_fam1
- `recursive_dfs_by_depth` — 1 family/families: lc102_fam2
- `recursive_dfs_traversal` — 1 family/families: lc547_fam2
- `recursive_merge` — 1 family/families: lc21_fam4
- `sort_and_rebuild` — 1 family/families: lc21_fam2

No corrected label has been added to the runtime vocabulary. Each gap above is a taxonomy candidate only (see the post-human-review report).
