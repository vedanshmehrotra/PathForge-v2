# Calendar-aware practice POC

`calendar_practice_v2` is an additive, deterministic practice policy. The normal frontend explicitly requests it through authenticated `/recommend` practice mode. Omitting the policy preserves `recorded_practice_v1`; omitting mode preserves legacy API behavior. This change does not alter detectors, ground truth, scoring eligibility, authority or Shadow defaults.

## User contract

No topic/difficulty setup is required. Offer at most three choices with concise, factual reasons:

- Return to a topic: a new problem sharing a specific catalog tag not recorded for seven elapsed days.
- Revisit a problem: when no related return is available, an older problem can be offered with its actual last recorded date.
- Continue a topic: a new problem sharing a specific tag with the latest dated practice.
- Try something different: vary catalog-topic exposure; cold starts receive starting choices.

These are alternative next actions, not a checklist. Difficulty and session skips remain optional hard constraints. All returned links are canonical, validated stored URLs; internal database IDs do not become guessed public IDs. A click does not mark completion. There is no correctness, weakness, mastery, forgetting-probability or predicted-gain claim.

## Evidence and implementation

`pathforge/calendar_practice.py` is pure. The practice service reads only existing catalog metadata and up to 1,001 problem-linked submission rows for the verified user; one row detects truncation of the 1,000-event policy window. V2 adds the existing `submitted_at` field to that read. It does not read diagnostic state, invoke a model, write records or introduce a migration.

Candidates come from `problems` through the existing catalog loader, without a join to ground truth. A catalog problem can therefore be recommended before its ground truth exists. A public problem absent from this catalog cannot appear until catalog ingestion adds its metadata; recommendation requests do not fetch or generate missing problems. Problem preparation and ground-truth generation remain separate, on-demand comparison operations, not prerequisites for recommendation ranking.

Valid timestamps must be timezone-aware, not future-dated, and parse as datetimes. Count a canonical URL once per UTC day; divide that exposure across its descriptive tags. Repeated analyses are not repeated achievements. Missing dates remain unknown; a URL with an unknown date cannot borrow an older valid date to justify a scheduled return. The newest supplied mapped record is withheld when dates are incomplete; otherwise the latest dated problem is withheld. Valid dated windows are order-invariant. Do not reinterpret a naive historical timestamp as UTC.

Use each specific tag's latest valid exposure for related-return eligibility, not an arbitrary old anchor. Unknown times for that tag suppress calendar-based related-return claims. A revisit uses that problem's latest known date and at least seven elapsed days. Broader recent practice does not prove or disprove recall of an individual problem.

Array(s), String(s), Matrix/Matrices, Linked List(s), Tree(s), Binary Tree(s) and Graph(s) are excluded from targeted relatedness. They still contribute to variety. For example, Two Sum and House Robber sharing only Array cannot establish a follow-up. This small explicit exclusion is a conservative heuristic, not a reviewed prerequisite ontology. Other shared tags still do not prove the same algorithm is required.

General ranking uses slate variety, proximity to the latest source difficulty, fractional topic exposure and stable URL order. Latest difficulty is context, not demonstrated ability. Canonical aliases share history/exclusions; conflicting identities or URL metadata are excluded. No unseen choices can be invented from an empty bank. Recent-only or undated exhausted banks return `caught_up`; skipped banks return `session_exhausted`; strict filters with no candidates return `no_candidates`. Older eligible revisits can fill an exhausted bank.

Compatibility fields remain (`reason` string, `pattern` empty, `score` null, neutral `summary`). Additive fields include policy/role, factual `reason_evidence` and history date diagnostics. Frontend hides legacy weakness/gain explanations and shows short role labels. Request changes/account changes retain existing stale-response protection.

## Research credibility and feasibility

Rules, revisit/follow-up mixtures, diversity and similarity are established ideas. The closest practical reference is [Pelánek et al.'s modular rule-based educational recommender](https://link.springer.com/article/10.1007/s11257-024-09396-z). [AtCoder Problems](https://kenkoooo.com/atcoder/book/en/recommend.html) provides actionable difficulty/repeat controls, while [Exercism](https://exercism.org/docs/building/product/unlocking-exercises) distinguishes structured learning and open practice. These products do not establish that PathForge can infer solving probability or prerequisites.

The abstract of [Hoq et al., pattern-based knowledge-component recommendations](https://arxiv.org/abs/2607.05409) also describes matching programming resources through extracted code concepts. Pattern-based relatedness alone is therefore not a defensible novelty claim. A research direction remains evaluation of useful, event-grounded practice choices under incomplete/unreliable diagnostics. Independence alone is insufficient: compare against equally isolated v1 and diverse general-choice baselines and measure usefulness independently of selector tags.

The policy uses the standard library and existing identity/link helpers, with approximately `O(N*T + H log H + H*T + 3*N*T)` work for N catalog items, bounded H events and T tags. No new service, runtime LLM, embedding API, model training or dependency is needed. No manual problem-approval workflow is introduced.

## Verification and limits

Run the new policy/service/route regressions and existing practice/link/authority/serialization tests with the offline guard **before backend imports**. Test actual API-produced responses in a local browser with mocked transport; that does not establish production data quality or authenticated live behavior. Source tests do not execute submitted programs.

Metadata may be sparse or wrong. Seven days is a heuristic, UTC day boundaries are explicit, and the history window is bounded. Topic overlap remains descriptive, not independent educational validation. Old data without usable dates gets general choices, not fabricated schedules. The API retains legacy mode; v2 safety claims apply only to the explicitly requested practice policy.

No impression-tracking table or feedback model is added. Learning gains, user trust, policy superiority and research novelty remain unverified. The next evaluation is a small, counterbalanced usability pilot with mixed daily histories and independent relatedness judgments. A later learning study needs prespecified delayed outcomes; clicks and analysis matches are not learning measurements. Additional content review in development is distinct from mandatory human approval in the application.
