"""B10 — strategy-specificity precision harness (evidence only).

Runs the B10 contract against nominated TECHNIQUE -> STRATEGY promotion
candidates and produces the evidence a human reviewer needs:

* shadow-presence vs legacy-namesake-presence breadth per corpus, with the
  **actual record ids** in every bucket (never counts alone);
* mismatch evidence samples for the flagged records;
* the four required negative-control classes, with the incidental-usage control
  evaluated for real;
* the recorded B3 -> B4 -> B5 -> B6 path;
* the contract verdict and its failing clauses.

It is **evidence only**. It never modifies Ground Truth, the registry or
``concepts.py``, never promotes a concept, never executes a product consequence
(no Elo, gap or recommendation path is imported), and cannot emit an approval:
its recommendation space is ``SAFE`` / ``UNSAFE`` / ``UNKNOWN``, where ``SAFE``
means "the evidence is complete enough for a human decision" and never "approved".

Run from the repository root:

    python experiments/code_analysis_evaluation/runners/strategy_specificity_measure.py
"""

import ast
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathforge.ast_analysis import lookup_specificity as specificity  # noqa: E402
from pathforge.ast_analysis import strategy_contract as sc  # noqa: E402
from pathforge.ast_analysis.shadow import shadow_runner  # noqa: E402
from pathforge.ast_analysis.shadow.data_structures import EXTRACTOR_VERSION  # noqa: E402
from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts  # noqa: E402
from pathforge.ast_analysis.shadow.relations import RELATIONS_VERSION, build_relations  # noqa: E402
from pathforge.ast_analysis.shadow.techniques import detect_techniques  # noqa: E402
from pathforge.services import product_eligibility as b6  # noqa: E402
from pathforge.services.ground_truth_builder import (  # noqa: E402
    mark_family_relations,
)

import src.ast_detection.detectors  # noqa: E402,F401  (triggers registration)
from src.ast_detection.registry import get_all_detectors  # noqa: E402

RESULTS = ROOT / "experiments" / "code_analysis_evaluation" / "results"
NATIVE_PATH = RESULTS / "db_batch3" / "submission_eval_results_NATIVE.json"
BENCHMARK_PATH = RESULTS / "disjoint301_eval_results_BASELINE_step4.json"
OUT_JSON = RESULTS / "strategy_specificity_measurement.json"
OUT_REVIEW = RESULTS / "strategy_specificity_review.md"

#: How many ``legacy_only`` cases carry a full source sample. The pattern is the
#: opposite direction of interest (shadow misses something legacy sees), so the
#: complete id list is kept and only the samples are capped.
LEGACY_SAMPLE_CAP = 5

SAFE = "SAFE"
UNSAFE = "UNSAFE"
UNKNOWN = "UNKNOWN"

PENDING = "_(pending human review)_"


# ============================================================================
# Corpus
# ============================================================================

@dataclass(frozen=True)
class CorpusRecord:
    record_id: str
    code: str
    groups: List[dict]
    corpus: str
    title: str = ""


def _native_records() -> Tuple[dict, List[CorpusRecord]]:
    payload = json.loads(NATIVE_PATH.read_text(encoding="utf-8"))
    records = [
        CorpusRecord(
            record_id=rec["external_submission_id"],
            code=rec["source_code"],
            groups=list(rec.get("groups") or []),
            corpus="native",
            title=rec.get("title") or "",
        )
        for rec in payload["records"]
    ]
    identity = {
        "path": str(NATIVE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "provenance": payload.get("provenance", "NATIVE"),
        "records": len(records),
    }
    return identity, records


def _benchmark_records() -> Tuple[dict, List[CorpusRecord]]:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    records = []
    for rec in payload["records"]:
        name = rec["name"]
        groups = [{
            "id": name,
            "required": list(rec.get("required_concepts") or []),
            "authority_tier": "llm_proposed",
            "patterns": [rec["expected_pattern"]] if rec.get("expected_pattern") else [],
        }]
        mark_family_relations(groups)
        records.append(CorpusRecord(
            record_id=name, code=rec["code"], groups=groups,
            corpus="benchmark", title=name,
        ))
    identity = {
        "path": str(BENCHMARK_PATH.relative_to(ROOT)).replace("\\", "/"),
        "provenance": payload.get("provenance", "NATIVE (llm_proposed GT)"),
        "records": len(records),
    }
    return identity, records


# ============================================================================
# Shadow + legacy measurement
# ============================================================================

_DETECTORS = {detector.pattern_id: detector for detector in get_all_detectors()}


def _shadow(code: str, groups: Optional[Sequence[dict]] = None) -> Optional[dict]:
    return shadow_runner.run_shadow_analysis(code, solution_groups=list(groups or []) or None)


def _concept_evidence(shadow: Optional[dict], concept_id: str) -> Optional[dict]:
    if not shadow or not shadow.get("evidence_state"):
        return None
    for item in shadow["evidence_state"]["evidence"]:
        if item["concept_id"] == concept_id:
            return item
    return None


def _shadow_present(shadow: Optional[dict], concept_id: str) -> bool:
    item = _concept_evidence(shadow, concept_id)
    return bool(item) and item["state"] == "PRESENT"


def _legacy_signals(
    tree: ast.AST, namesakes: Sequence[str]
) -> Tuple[List[str], List[str]]:
    """Return ``(detected, evidence_only)`` for the namesake detectors.

    ``detected`` is the legacy system's own answer: the coordinator filters its
    results with ``result.evidence and result.detected`` before they reach
    ``detected_patterns``, so this — not merely a non-zero confidence — is what
    the legacy verdict is built from. ``evidence_only`` records the softer
    signal (a detector emitted evidence but declined to claim the pattern); it
    is reported alongside so the two can never be confused.
    """
    detected: List[str] = []
    evidence_only: List[str] = []
    for pattern_id in namesakes:
        detector = _DETECTORS.get(pattern_id)
        if detector is None:
            continue
        try:
            result = detector.detect(tree)
        except Exception:  # pragma: no cover - a detector failure is reported
            detected.append(f"{pattern_id}:ERROR")
            continue
        if result.detected:
            detected.append(pattern_id)
        elif result.evidence and result.confidence > 0.0:
            evidence_only.append(pattern_id)
    return detected, evidence_only


def _excerpt(code: str, limit: int = 6, width: int = 120) -> str:
    lines = [line.rstrip() for line in code.splitlines() if line.strip()]
    body = " | ".join(lines[:limit])
    return body[:width]


def _validate_namesakes(spec: "CandidateSpec") -> List[dict]:
    """Confirm every declared namesake really references the concept.

    The namesake is not taken on trust: a declared pattern must carry the
    concept in its V1 mapping (``required`` or ``optional``).
    """
    resolved = []
    mapping = _PATTERN_TO_V1_MAPPING
    for pattern_id in spec.namesakes:
        entry = mapping.get(pattern_id)
        if entry is None:
            raise ValueError(
                f"{spec.concept_id}: namesake {pattern_id!r} is not a mapped pattern"
            )
        if spec.concept_id in (entry.get("required") or []):
            relation = "required"
        elif spec.concept_id in (entry.get("optional") or []):
            relation = "optional"
        else:
            raise ValueError(
                f"{spec.concept_id}: namesake {pattern_id!r} does not reference it"
            )
        resolved.append({
            "pattern_id": pattern_id,
            "relation": relation,
            "legacy_detector": pattern_id in _DETECTORS,
        })
    return resolved


@dataclass
class Measurement:
    counts: Dict[str, int] = field(default_factory=lambda: {
        "both": 0, "shadow_only": 0, "legacy_only": 0, "neither": 0,
    })
    ids: Dict[str, List[str]] = field(default_factory=lambda: {
        "both": [], "shadow_only": [], "legacy_only": [], "error": [],
    })
    #: Soft signal: the namesake detector emitted evidence but did not claim the
    #: pattern. Never part of the buckets; recorded so the difference is visible.
    evidence_only_ids: List[str] = field(default_factory=list)
    samples: List[dict] = field(default_factory=list)


def _measure_corpus(
    spec: "CandidateSpec", records: Sequence[CorpusRecord]
) -> Measurement:
    measurement = Measurement()
    for record in records:
        try:
            tree = ast.parse(record.code)
        except SyntaxError:
            measurement.ids["error"].append(record.record_id)
            continue
        shadow = _shadow(record.code, record.groups)
        item = _concept_evidence(shadow, spec.concept_id)
        if item is None:
            measurement.ids["error"].append(record.record_id)
            continue
        shadow_here = item["state"] == "PRESENT"
        fired, evidence_only = _legacy_signals(tree, spec.namesakes)
        legacy_here = any(not f.endswith(":ERROR") for f in fired)
        if evidence_only:
            measurement.evidence_only_ids.append(record.record_id)

        if shadow_here and legacy_here:
            bucket = "both"
        elif shadow_here:
            bucket = "shadow_only"
        elif legacy_here:
            bucket = "legacy_only"
        else:
            measurement.counts["neither"] += 1
            continue
        measurement.counts[bucket] += 1
        measurement.ids[bucket].append(record.record_id)
        if bucket == "shadow_only" or (
            bucket == "legacy_only"
            and len([s for s in measurement.samples if s["bucket"] == "legacy_only"])
            < LEGACY_SAMPLE_CAP
        ):
            measurement.samples.append({
                "bucket": bucket,
                "record_id": record.record_id,
                "corpus": record.corpus,
                "title": record.title,
                "concept_state": item["state"],
                "concept_evidence_refs": list(item.get("evidence_refs") or []),
                "legacy_fired": fired,
                "legacy_absent": not fired,
                "legacy_evidence_only": evidence_only,
                "code_excerpt": _excerpt(record.code),
            })
    return measurement


def _to_contract_measurement(corpus: str, measurement: Measurement) -> sc.CorpusMeasurement:
    return sc.CorpusMeasurement(
        corpus=corpus,
        both_ids=tuple(measurement.ids["both"]),
        shadow_only_ids=tuple(measurement.ids["shadow_only"]),
        legacy_only_ids=tuple(measurement.ids["legacy_only"]),
        neither_count=measurement.counts["neither"],
        error_ids=tuple(measurement.ids["error"]),
    )


# ============================================================================
# B11 strategy specificity (key provenance)
# ============================================================================

#: The declared discriminator whose availability the B11 relation layer decides.
_KEY_ORIGIN_DISCRIMINATOR = "key_origin"


def _strategy_specificity(code: str, concept_id: str):
    """The B11 specificity verdict, or ``None`` when the concept does not fire.

    Raw technique presence is untouched. This reads the cited mapping fact and
    the shared relations bundle and answers only whether the citation is
    specific enough to support an algorithmic conclusion.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    facts = extract_structural_facts(tree)
    relations = build_relations(tree)
    evidence = next(
        (t for t in detect_techniques(facts, relations=relations)
         if t.technique_id == concept_id),
        None,
    )
    return specificity.evaluate_evidence_specificity(evidence, facts, relations)


def _key_origin_measurement(
    spec: "CandidateSpec", corpora: Dict[str, List[CorpusRecord]]
) -> Tuple[sc.Separation, Dict[str, int]]:
    """Measure the key-provenance discriminator over both corpora.

    Ground-truth anchor: a record the discriminator calls strategy-eligible but
    whose own required set does not name the concept is an over-coverage entry —
    the positive form holds where the concept is not the approach. Refused
    records are the ones the specificity rule declines to establish.
    """
    eligible: List[str] = []
    refused: List[str] = []
    over_covered: List[str] = []
    states: Dict[str, int] = {}
    for records in corpora.values():
        for record in records:
            verdict = _strategy_specificity(record.code, spec.concept_id)
            if verdict is None:
                continue
            states[verdict.state] = states.get(verdict.state, 0) + 1
            if not verdict.strategy_eligible:
                refused.append(record.record_id)
                continue
            requires = any(
                spec.concept_id in (group.get("required") or [])
                for group in record.groups
            )
            (eligible if requires else over_covered).append(record.record_id)
    return sc.Separation(
        positive_records=tuple(eligible),
        negative_records=tuple(refused),
        misclassified=tuple(over_covered),
    ), states


def _measured_discriminators(
    spec: "CandidateSpec",
    separation: Optional[sc.Separation],
    states: Dict[str, int],
) -> Tuple[sc.Discriminator, ...]:
    """Attach the measured separation to the declared key-provenance rule.

    Only that one discriminator is touched; every other declaration (and every
    other candidate's declarations) is returned unchanged, so no unrelated
    verdict can move.
    """
    if separation is None:
        return spec.discriminators
    measured = []
    for discriminator in spec.discriminators:
        if discriminator.name != _KEY_ORIGIN_DISCRIMINATOR:
            measured.append(discriminator)
            continue
        state_summary = ", ".join(f"{k}={v}" for k, v in sorted(states.items()))
        measured.append(replace(
            discriminator,
            source=f"{sc.SOURCE_RELATION}:lookup_key_origins",
            availability=sc.AVAILABLE,
            separates=separation,
            evidence_ref=(
                "B11 measurement over native 46 + benchmark 301 and the four "
                f"control classes; specificity states: {state_summary}"
            ),
        ))
    return tuple(measured)


def _specificity_block(
    separation: Optional[sc.Separation], states: Dict[str, int]
) -> Optional[dict]:
    """The strategy-specificity evidence for one candidate, if it has a rule."""
    if separation is None:
        return None
    return {
        "version": specificity.SPECIFICITY_VERSION,
        "relation": "lookup_key_origins",
        "states": states,
        "key_origin_separation": separation.to_dict(),
        "note": (
            "B11 evaluates whether the mapping cited by the detected evidence "
            "is specific enough for an algorithmic strategy conclusion; raw "
            "technique presence is never changed and nothing is promoted"
        ),
    }


# ============================================================================
# Negative controls (evaluated for real)
# ============================================================================

def _control(spec: "CandidateSpec", name: str) -> Optional[sc.Control]:
    cases = spec.controls.get(name) or ()
    if not cases:
        return None
    confirms = any(
        _shadow_present(_shadow(code), spec.concept_id) for _, code in cases
    )
    return sc.Control(
        name=name, cases=tuple(label for label, _ in cases), confirms=confirms,
    )


def _negative_controls(spec: "CandidateSpec") -> sc.NegativeControls:
    return sc.NegativeControls(
        positive=_control(spec, "positive"),
        negative=_control(spec, "negative"),
        adversarial=_control(spec, "adversarial"),
        incidental_usage=_control(spec, "incidental_usage"),
    )


# ============================================================================
# B3 -> B6 path
# ============================================================================

def _authority_path(
    spec: "CandidateSpec", records: Sequence[CorpusRecord]
) -> Tuple[dict, dict]:
    """The recorded B3 -> B6 path for the families that require the concept."""
    coverage_states: Dict[str, int] = {}
    tiers: Dict[str, int] = {}
    primaries: Dict[str, int] = {}
    authoritative = False
    eligible = False
    families = 0
    required_sets: List[List[str]] = []
    one_of: List[str] = []

    for record in records:
        required_here = [
            list(group.get("required") or [])
            for group in record.groups
            if spec.concept_id in (group.get("required") or [])
        ]
        if not required_here:
            continue
        required_sets.extend(required_here)
        one_of.extend(sorted({
            str(group.get("alternative_group_id"))
            for group in record.groups
            if group.get("family_relation") == "ONE_OF"
            and spec.concept_id in (group.get("required") or [])
        }))
        shadow = _shadow(record.code, record.groups)
        if not shadow:
            continue
        selection = ((shadow.get("strategy_selection") or {}).get("submission")
                     or {}).get("selected")
        primaries[str(selection)] = primaries.get(str(selection), 0) + 1
        for family in (shadow.get("coverage") or {}).get("families") or []:
            if spec.concept_id not in (family.get("required") or []):
                continue
            if spec.concept_id not in (family.get("identifying_required") or []):
                continue
            families += 1
            state = family.get("coverage_state")
            coverage_states[state] = coverage_states.get(state, 0) + 1
        for family in (shadow.get("authority") or {}).get("families") or []:
            tier = family.get("authority_tier")
            tiers[tier] = tiers.get(tier, 0) + 1
            authoritative = authoritative or bool(family.get("authoritative"))
        if shadow.get("authority"):
            report = b6.product_eligibility(b6._report_from_dict(shadow["authority"]))
            eligible = eligible or bool(report.eligible)

    def _top(counts: Dict[str, int]) -> str:
        return max(counts, key=lambda key: counts[key]) if counts else ""

    path = {
        "records_requiring_concept": sum(
            1 for record in records
            if any(spec.concept_id in (g.get("required") or []) for g in record.groups)
        ),
        "families_identified_by_concept": families,
        "coverage_states": coverage_states,
        "b4_selection_counts": primaries,
        "authoritative": authoritative,
        "b6_eligible": eligible,
        "authority_tiers": tiers,
        "one_of_memberships": sorted({group for group in one_of if group and group != "None"}),
        "note": (
            "recorded before any change; promotion is not applied, so this is the "
            "current path, not a post-promotion forecast"
        ),
    }
    evidence = {
        "b3_coverage": _top(coverage_states),
        "b4_primary": None if _top(primaries) in ("", "None") else _top(primaries),
        "b5_authoritative": authoritative,
        "b6_eligible": eligible,
        "authority_tier": _top(tiers),
    }
    return path, evidence


# ============================================================================
# Review file
# ============================================================================

_REVIEW_ROW = re.compile(
    r"^\|\s*(?P<record>[^|]*?)\s*\|\s*(?P<corpus>[^|]*?)\s*\|\s*"
    r"(?P<candidate>[^|]*?)\s*\|\s*(?P<state>[^|]*?)\s*\|\s*"
    r"(?P<classification>[^|]*?)\s*\|\s*(?P<reviewer>[^|]*?)\s*\|\s*"
    r"(?P<date>[^|]*?)\s*\|\s*(?P<note>[^|]*?)\s*\|\s*$"
)


def _normalise_reviews(path: pathlib.Path) -> Dict[str, List[sc.ReviewEntry]]:
    """Rows of the review file, keyed by candidate. Unclassified rows stay open."""
    by_candidate: Dict[str, List[sc.ReviewEntry]] = {}
    if not path.exists():
        return by_candidate
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _REVIEW_ROW.match(line)
        if not match or match.group("record") in ("record", "---"):
            continue
        classification = match.group("classification").strip().upper()
        if classification not in sc.REVIEW_CLASSIFICATIONS:
            classification = ""
        def _clean(value: str) -> str:
            value = value.strip()
            return "" if value in ("", PENDING) else value
        by_candidate.setdefault(match.group("candidate"), []).append(
            sc.ReviewEntry(
                record_id=match.group("record").strip(),
                classification=classification,
                reviewer=_clean(match.group("reviewer")),
                date=_clean(match.group("date")),
                note=_clean(match.group("note")),
            )
        )
    return by_candidate


def _write_review_template(rows: List[dict]) -> None:
    lines = [
        "# B10 — strategy-specificity review queue",
        "",
        "One row per `shadow_only` record (the candidate's concept is `PRESENT` while",
        "its legacy namesake is absent). Legacy is a comparison axis, not an oracle: a",
        "`shadow_only` record may be a legitimate improvement, a false detection, a",
        "representation difference, or unresolved ambiguity.",
        "",
        "Fill `classification` with one of `LEGITIMATE_IMPROVEMENT`,",
        "`FALSE_CONFIRMATION`, `REPRESENTATION_DIFFERENCE`, `UNRESOLVED`, plus a",
        "`reviewer` and a `date`. An empty reviewer, or any `UNRESOLVED` /",
        "`FALSE_CONFIRMATION` row, keeps contract clause C3 blocked. This file is",
        "edited by a human; the harness only creates it and reads it back.",
        "",
        "| record | corpus | candidate | concept state | classification | reviewer | date | note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['record_id']} | {row['corpus']} | {row['candidate']} | "
            f"{row['state']} | {PENDING} |  |  |  |"
        )
    lines.append("")
    OUT_REVIEW.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# Candidate specifications (data only — no rule lives here)
# ============================================================================

_TWO_SUM_ONLINE = (
    "class Solution:\n"
    "    def twoSum(self, nums, target):\n"
    "        seen = {}\n"
    "        for i, num in enumerate(nums):\n"
    "            complement = target - num\n"
    "            if complement in seen:\n"
    "                return [seen[complement], i]\n"
    "            seen[num] = i\n"
    "        return []\n"
)
_DICT_CTOR_MEMBERSHIP = (
    "class Solution:\n"
    "    def solve(self, words):\n"
    "        table = dict()\n"
    "        for w in words:\n"
    "            if w in table:\n"
    "                return table[w]\n"
    "            table[w] = len(w)\n"
    "        return None\n"
)
_SET_MEMBERSHIP = (
    "def f(nums):\n"
    "    seen = set()\n"
    "    for n in nums:\n"
    "        if n in seen:\n"
    "            return True\n"
    "        seen.add(n)\n"
    "    return False\n"
)
_LIST_MEMBERSHIP = (
    "def f(nums):\n"
    "    lst = []\n"
    "    for x in nums:\n"
    "        if x not in lst:\n"
    "            lst.append(x)\n"
    "    return lst\n"
)
_INPUT_ARRAY_MEMBERSHIP = (
    "def f(nums):\n"
    "    s = nums[0]\n"
    "    while s in nums:\n"
    "        s += 1\n"
    "    return s\n"
)
_COUNTER_MEMBERSHIP = (
    "def f(s):\n"
    "    n = Counter()\n"
    "    for c in s:\n"
    "        n[c] += 1\n"
    "        if c in n:\n"
    "            pass\n"
    "    return n\n"
)
_RECURSION_MEMO = (
    "class Solution:\n"
    "    def climbStairs(self, n):\n"
    "        memo = {}\n"
    "        def dfs(x):\n"
    "            if x <= 2:\n"
    "                return x\n"
    "            if x in memo:\n"
    "                return memo[x]\n"
    "            memo[x] = dfs(x - 1) + dfs(x - 2)\n"
    "            return memo[x]\n"
    "        return dfs(n)\n"
)
_WRITE_ONLY_DICT = (
    "class Solution:\n"
    "    def nextGreaterElement(self, nums1, nums2):\n"
    "        stack = []\n"
    "        mp = {}\n"
    "        for x in nums2:\n"
    "            while stack and stack[-1] < x:\n"
    "                mp[stack.pop()] = x\n"
    "            stack.append(x)\n"
    "        ans = []\n"
    "        for x in nums1:\n"
    "            ans.append(mp.get(x, -1))\n"
    "        return ans\n"
)
_UNGATED_READ_ONLY = (
    "class Solution:\n"
    "    def solve(self, nums):\n"
    "        d = {}\n"
    "        for n in nums:\n"
    "            d[n] = n * 2\n"
    "            v = d[n]\n"
    "        return d\n"
)
_ROMAN_VALUE_TABLE = (
    "class Solution:\n"
    "    def romanToInt(self, s):\n"
    "        hashm = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}\n"
    "        val = 0\n"
    "        for i in range(len(s)):\n"
    "            if val == 0:\n"
    "                val += hashm[s[i]]\n"
    "            elif s[i] == s[i - 1] or hashm[s[i]] > hashm[s[i - 1]]:\n"
    "                val += hashm[s[i]]\n"
    "            else:\n"
    "                val -= hashm[s[i]]\n"
    "        return val\n"
)
_BRACKET_PAIR_TABLE = (
    "class Solution:\n"
    "    def isValid(self, s):\n"
    "        pairs = {')': '(', ']': '[', '}': '{'}\n"
    "        stack = []\n"
    "        for ch in s:\n"
    "            if ch in pairs:\n"
    "                if not stack or stack.pop() != pairs[ch]:\n"
    "                    return False\n"
    "            else:\n"
    "                stack.append(ch)\n"
    "        return not stack\n"
)

_PREFIX_SUM_LOOP = (
    "def f(nums, k):\n"
    "    total = 0\n"
    "    best = 0\n"
    "    for x in nums:\n"
    "        total += x\n"
    "        if total == k:\n"
    "            best = total\n"
    "    return best\n"
)
_RUNNING_TOTAL = (
    "def f(nums):\n"
    "    out = []\n"
    "    running = 0\n"
    "    for x in nums:\n"
    "        running += x\n"
    "        out.append(running)\n"
    "    return out\n"
)
_RUNNING_MAX = (
    "def f(xs):\n"
    "    best = xs[0]\n"
    "    for x in xs[1:]:\n"
    "        if x > best:\n"
    "            best = x\n"
    "    return best\n"
)
_EXPONENTIATION = (
    "def power(x, n):\n"
    "    result = 1\n"
    "    while n > 0:\n"
    "        if n % 2 == 1:\n"
    "            result *= x\n"
    "        x *= x\n"
    "        n //= 2\n"
    "    return result\n"
)
_DIGIT_SUM = (
    "def f(n):\n"
    "    s = 0\n"
    "    while n > 0:\n"
    "        s += n % 10\n"
    "        n //= 10\n"
    "    return s\n"
)
_BARE_COUNT = (
    "def f(xs):\n"
    "    c = 0\n"
    "    for x in xs:\n"
    "        c += 1\n"
    "    return c\n"
)

_NESTED_BEST_CANDIDATE = (
    "def f(items):\n"
    "    best = None\n"
    "    best_score = 0\n"
    "    for item in items:\n"
    "        for other in items:\n"
    "            if item == other:\n"
    "                continue\n"
    "            score = len(item) + len(other)\n"
    "            if score > best_score:\n"
    "                best_score = score\n"
    "                best = (item, other)\n"
    "    return best\n"
)
_SINGLE_PASS_REDUCE = (
    "def f(xs):\n"
    "    total = 0\n"
    "    for x in xs:\n"
    "        total += x\n"
    "    return total\n"
)
_SORTED_EXTREMAL_READ = (
    "class Solution:\n"
    "    def maximumProduct(self, nums):\n"
    "        nums.sort()\n"
    "        return max(nums[0] * nums[1] * nums[-1], nums[-1] * nums[-2] * nums[-3])\n"
)
_INTERVAL_SWEEP = (
    "def f(intervals):\n"
    "    intervals.sort(key=lambda pair: pair[1])\n"
    "    count = 0\n"
    "    last_end = float('-inf')\n"
    "    for start, end in intervals:\n"
    "        if start >= last_end:\n"
    "            count += 1\n"
    "            last_end = end\n"
    "    return count\n"
)

_SAME_DIRECTION_POINTERS = (
    "def f(nums):\n"
    "    slow = 0\n"
    "    for fast in range(len(nums)):\n"
    "        if nums[fast] != 0:\n"
    "            nums[slow] = nums[fast]\n"
    "            slow += 1\n"
    "    return slow\n"
)
_OPPOSITE_DIRECTION_SCAN = (
    "def f(s):\n"
    "    left = 0\n"
    "    right = len(s) - 1\n"
    "    while left < right:\n"
    "        if s[left] != s[right]:\n"
    "            return False\n"
    "        left += 1\n"
    "        right -= 1\n"
    "    return True\n"
)
_MERGE_TWO_LISTS = (
    "class Solution:\n"
    "    def mergeTwoLists(self, list1, list2):\n"
    "        head = tail = ListNode(0)\n"
    "        while list1 and list2:\n"
    "            if list1.val <= list2.val:\n"
    "                tail.next = list1\n"
    "                list1 = list1.next\n"
    "            else:\n"
    "                tail.next = list2\n"
    "                list2 = list2.next\n"
    "            tail = tail.next\n"
    "        tail.next = list1 or list2\n"
    "        return head.next\n"
)
_FLOYD_CYCLE = (
    "class Solution:\n"
    "    def hasCycle(self, head):\n"
    "        slow = fast = head\n"
    "        while fast and fast.next:\n"
    "            slow = slow.next\n"
    "            fast = fast.next.next\n"
    "            if slow is fast:\n"
    "                return True\n"
    "        return False\n"
)


@dataclass(frozen=True)
class CandidateSpec:
    concept_id: str
    namesakes: Tuple[str, ...]
    identity_meaning: str
    identity_is_mechanism_only: bool
    rationale: str
    discriminators: Tuple[sc.Discriminator, ...]
    controls: Dict[str, Tuple[Tuple[str, str], ...]]
    parity_deltas: Tuple[sc.ParityDelta, ...] = ()


CANDIDATES: Tuple[CandidateSpec, ...] = (
    CandidateSpec(
        concept_id="hash_lookup",
        namesakes=("hash_map_lookup",),
        identity_meaning=(
            "single-pass complement lookup: build a key->value mapping as the scan "
            "progresses and test key presence on it to replace a nested search"
        ),
        identity_is_mechanism_only=False,
        rationale=(
            "The intended meaning is an approach, but the technique deliberately "
            "also accepts a gated read of a static reference table, so the same "
            "evidence covers a tool (B9 db-33 investigation)."
        ),
        discriminators=(
            sc.Discriminator(
                name="incremental_keyed_lookup",
                source="fact:mapping_construction",
                positive_form=(
                    "the mapping is constructed empty and written inside the loop "
                    "while a key-presence test on that same mapping gates control flow"
                ),
                negative_form=(
                    "the mapping is a static literal that is only read, so no "
                    "in-loop construction and no key-presence test occur"
                ),
                availability=sc.AVAILABLE,
                separates=sc.Separation(
                    positive_records=("db-11", "db-39", "hm_two_sum_map",
                                      "hm_valid_anagram"),
                    negative_records=("db-33", "hm_roman_to_int",
                                      "stack_valid_parens"),
                    misclassified=("hm_memoize_expensive", "hm_adjacency_list"),
                ),
                evidence_ref=(
                    "B9/B10 measurements: native 46 + benchmark 301; the two "
                    "misclassified records carry the full dynamic signature but "
                    "describe a cache and an adjacency store"
                ),
                note=(
                    "Measured to over-cover: the positive form does not separate "
                    "approach-use from tool-use."
                ),
            ),
            sc.Discriminator(
                name="key_origin",
                source="derived:key_provenance",
                positive_form=(
                    "the cited mapping is built and probed by the scan - its keys "
                    "resolve to computed, element or loop-target provenance - so "
                    "the lookup is algorithmic rather than a static table or an "
                    "externally keyed store"
                ),
                negative_form=(
                    "the cited mapping is an immutable dict literal (a reference "
                    "table), or every lookup key is a function parameter and the "
                    "mapping is never updated (a caller-keyed cache)"
                ),
                # Availability and the measured separation are attached at
                # measurement time (see `_measured_discriminators`), because the
                # separation can only be measured against a corpus.
                availability=sc.NEEDS_EXTRACTION,
                evidence_ref=(
                    "B11: SubmissionRelations.lookup_key_origins supplies the "
                    "key-provenance relation this discriminator needed; the rule "
                    "lives in pathforge/ast_analysis/lookup_specificity.py"
                ),
            ),
        ),
        controls={
            "positive": (("two_sum_online_map", _TWO_SUM_ONLINE),
                         ("dict_ctor_membership", _DICT_CTOR_MEMBERSHIP)),
            "negative": (("set_membership", _SET_MEMBERSHIP),
                         ("list_membership", _LIST_MEMBERSHIP),
                         ("input_array_membership", _INPUT_ARRAY_MEMBERSHIP)),
            "adversarial": (("counter_membership", _COUNTER_MEMBERSHIP),
                            ("recursion_memo", _RECURSION_MEMO),
                            ("write_only_dict", _WRITE_ONLY_DICT),
                            ("ungated_read_only", _UNGATED_READ_ONLY)),
            "incidental_usage": (
                ("roman_static_value_table", _ROMAN_VALUE_TABLE),
                ("bracket_pair_table", _BRACKET_PAIR_TABLE),
            ),
        },
        parity_deltas=(
            sc.ParityDelta(
                category="P5_LEGACY_NO_MATCH_SHADOW_CONFIRMED",
                count=1,
                classification=sc.NEW_DISAGREEMENT,
                evidence_ref=(
                    "B9 db-33 investigation: the promotion would confirm a "
                    "P1_EXACT_PARITY record as P5"
                ),
                projected=True,
            ),
        ),
    ),
    CandidateSpec(
        concept_id="sequential_accumulation",
        namesakes=("prefix_sum",),
        identity_meaning=(
            "running accumulator over a sequence, used to answer range or "
            "subarray-sum questions"
        ),
        identity_is_mechanism_only=True,
        rationale=(
            "The producer fires on any loop that accumulates (a bare counter, a "
            "digit sum), so the stated meaning is a mechanism rather than the "
            "approach of the families that require it."
        ),
        discriminators=(
            sc.Discriminator(
                name="prefix_index_lookback",
                source="fact:index_lookback",
                positive_form=(
                    "the accumulator is combined with an earlier position of the "
                    "same sequence (a prefix/DP recurrence)"
                ),
                negative_form="the accumulator is a scalar tally with no lookback",
                availability=sc.AVAILABLE,
                separates=sc.Separation(
                    positive_records=("ps_subarray_equals_k", "ps_running_total_transform"),
                    negative_records=("bs_search_rotated",),
                    misclassified=("db-33", "hm_roman_to_int"),
                ),
                evidence_ref=(
                    "B9 measurements: index_lookback is PRESENT on the Roman "
                    "subtractive scan, so the fact does not separate a prefix-sum "
                    "approach from a running total"
                ),
                note="Measured to over-cover.",
            ),
            sc.Discriminator(
                name="sequence_question_shape",
                source="derived:sequence_aggregate_intent",
                positive_form=(
                    "the accumulated value answers a range/subarray question rather "
                    "than being the final answer itself"
                ),
                negative_form="the accumulator is the answer (a sum, a count)",
                availability=sc.NOT_AVAILABLE,
                evidence_ref="no fact or relation models the question being answered",
            ),
        ),
        controls={
            "positive": (("prefix_sum_loop", _PREFIX_SUM_LOOP),
                         ("running_total", _RUNNING_TOTAL)),
            "negative": (("running_max", _RUNNING_MAX),),
            "adversarial": (("exponentiation_by_squaring", _EXPONENTIATION),),
            "incidental_usage": (("digit_sum", _DIGIT_SUM),
                                 ("bare_counter", _BARE_COUNT)),
        },
    ),
    CandidateSpec(
        concept_id="candidate_selection",
        namesakes=("greedy_local",),
        identity_meaning=(
            "greedy local choice: maintain the best-scoring candidate seen so far "
            "under a comparison and return it"
        ),
        identity_is_mechanism_only=False,
        rationale=(
            "B9 classified the family as too generic: the same evidence covers "
            "nested-loop extremal reads, so no discriminator separates a greedy "
            "choice from a generic scan."
        ),
        discriminators=(
            sc.Discriminator(
                name="choice_constrains_continuation",
                source="derived:greedy_choice_structure",
                positive_form=(
                    "the selected candidate determines what the remaining search "
                    "may still consider"
                ),
                negative_form=(
                    "the candidate is only reported; the search space is unchanged"
                ),
                availability=sc.NOT_AVAILABLE,
                evidence_ref=(
                    "no fact or relation models whether the choice constrains the "
                    "remaining search"
                ),
            ),
        ),
        controls={
            "positive": (("nested_best_candidate", _NESTED_BEST_CANDIDATE),),
            "negative": (("single_pass_reduce", _SINGLE_PASS_REDUCE),),
            "adversarial": (("interval_sweep", _INTERVAL_SWEEP),),
            "incidental_usage": (("sorted_extremal_read", _SORTED_EXTREMAL_READ),),
        },
    ),
    CandidateSpec(
        concept_id="forward_pointer_advance",
        namesakes=("fast_slow_pointers", "two_pointers_same"),
        identity_meaning=(
            "same-direction pointer advancement used to compact, merge or traverse "
            "a sequence in one pass"
        ),
        identity_is_mechanism_only=False,
        rationale=(
            "B9 classified the family as an implementation detail shared by "
            "distinct algorithms (cycle detection, merge, partition)."
        ),
        discriminators=(
            sc.Discriminator(
                name="pointer_velocity_relation",
                source="relation:updated_in_loop",
                positive_form=(
                    "one pointer advances a constant number of steps per iteration "
                    "relative to another (a cycle-detection invariant)"
                ),
                negative_form="both pointers advance the same way (a plain scan)",
                availability=sc.NEEDS_EXTRACTION,
                evidence_ref=(
                    "updated_in_loop records only which loop kinds a variable is "
                    "updated in, not per-iteration step ratios"
                ),
            ),
            sc.Discriminator(
                name="two_sequence_merge_shape",
                source="derived:multi_sequence_merge",
                positive_form=(
                    "two independent input sequences are consumed by a shared "
                    "advancing front"
                ),
                negative_form="a single sequence is scanned by one front",
                availability=sc.NOT_AVAILABLE,
                evidence_ref=(
                    "no fact or relation distinguishes two input sequences being "
                    "merged from a single-sequence scan"
                ),
            ),
        ),
        controls={
            "positive": (("same_direction_compaction", _SAME_DIRECTION_POINTERS),),
            "negative": (("opposite_direction_scan", _OPPOSITE_DIRECTION_SCAN),),
            "adversarial": (("merge_two_lists", _MERGE_TWO_LISTS),),
            "incidental_usage": (("floyd_cycle_detection", _FLOYD_CYCLE),),
        },
    ),
)


# ============================================================================
# Measurement
# ============================================================================

_PATTERN_TO_V1_MAPPING: Dict[str, dict] = {}


def _load_mapping() -> None:
    from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING

    _PATTERN_TO_V1_MAPPING.update(PATTERN_TO_V1_MAPPING)


def _recommendation(verdict: sc.ContractVerdict) -> str:
    if verdict.verdict == sc.NOT_EVALUABLE:
        return UNKNOWN
    if verdict.verdict == sc.BLOCKED:
        return UNSAFE
    return SAFE


def _measure_candidate(
    spec: CandidateSpec,
    corpora: Dict[str, List[CorpusRecord]],
    reviews: Dict[str, List[sc.ReviewEntry]],
) -> dict:
    metadata = sc.concept_metadata(spec.concept_id)
    namesakes = _validate_namesakes(spec)
    measurements: Dict[str, Measurement] = {}
    contract_measurements = []
    required_sets: List[str] = []
    appears_in_gt = False

    for corpus, records in corpora.items():
        measurement = _measure_corpus(spec, records)
        measurements[corpus] = measurement
        contract_measurements.append(_to_contract_measurement(corpus, measurement))
        for record in records:
            for group in record.groups:
                if spec.concept_id in (group.get("required") or []):
                    appears_in_gt = True
                    required_sets.append(",".join(group.get("required") or []))

    precision = sc.PrecisionEvidence(
        measurements=tuple(contract_measurements),
        reviews=tuple(reviews.get(spec.concept_id) or ()),
    )
    controls = _negative_controls(spec)
    separation, specificity_states = (
        _key_origin_measurement(spec, corpora)
        if any(d.name == _KEY_ORIGIN_DISCRIMINATOR for d in spec.discriminators)
        else (None, {})
    )
    authority_path, authority_evidence = _authority_path(
        spec, [r for records in corpora.values() for r in records]
    )
    required_concepts = tuple(sorted(set(required_sets)))[:6]

    candidate = sc.Candidate(
        concept_id=spec.concept_id,
        identity_meaning=spec.identity_meaning,
        identity_is_mechanism_only=spec.identity_is_mechanism_only,
        discriminators=_measured_discriminators(
            spec, separation, specificity_states
        ),
        precision=precision,
        negative_controls=controls,
        gt=sc.GTCompatibility(
            required_concepts=required_concepts or (spec.concept_id,),
            family_role=str(metadata.get("family_role", "")),
            tier=str(metadata.get("tier", "")),
            one_of_memberships=tuple(authority_path["one_of_memberships"]),
            identification_preserved=True,
            gt_relabel_required=False,
            family_semantics_preserved=False,
            semantic_change_declared=True,
            justification_basis=sc.BASIS_STRUCTURAL,
        ),
        primary_strategy=sc.PrimaryStrategySafety(),
        authority=sc.AuthorityImpact(
            path_evaluated=True,
            justification_basis=sc.BASIS_STRUCTURAL,
            **authority_evidence,
        ),
        parity=sc.ParityImpact(
            baseline_ref="results/b7_parity_measurement.json",
            deltas=spec.parity_deltas,
            justification_basis=sc.BASIS_STRUCTURAL,
        ),
        regression=sc.RegressionEvidence(),
        registered=bool(metadata),
        concept_class=str(metadata.get("class", "")),
        has_shadow_producer=sc.has_shadow_producer(spec.concept_id),
        namesakes=tuple(spec.namesakes),
        appears_in_corpus_gt=appears_in_gt,
    )
    verdict = sc.evaluate(candidate)

    flagged = list(precision.flagged_ids())
    reviewed = [
        entry for entry in precision.reviews
        if entry.record_id in flagged and entry.is_complete()
    ]

    result = {
        "concept": spec.concept_id,
        "concept_metadata": metadata,
        "identity": {
            "meaning": spec.identity_meaning,
            "mechanism_only": spec.identity_is_mechanism_only,
            "rationale": spec.rationale,
        },
        "producer": {
            "has_shadow_producer": candidate.has_shadow_producer,
            "sources": metadata.get("sources", []),
        },
        "namesakes": namesakes,
        "measurements": {
            corpus: {
                "counts": measurement.counts,
                "both_ids": measurement.ids["both"],
                "shadow_only_ids": measurement.ids["shadow_only"],
                "legacy_only_ids": measurement.ids["legacy_only"],
                "legacy_evidence_only_ids": measurement.evidence_only_ids,
                "legacy_evidence_only": len(measurement.evidence_only_ids),
                "error_ids": measurement.ids["error"],
            }
            for corpus, measurement in measurements.items()
        },
        "mismatch_samples": {
            corpus: measurement.samples for corpus, measurement in measurements.items()
        },
        "negative_controls": controls.to_dict(),
        "authority_path": authority_path,
        "parity": {
            "baseline_ref": "results/b7_parity_measurement.json",
            "deltas": [
                {
                    "category": delta.category, "count": delta.count,
                    "classification": delta.classification,
                    "projected": delta.projected,
                    "evidence_ref": delta.evidence_ref,
                }
                for delta in spec.parity_deltas
            ],
        },
        "review": {
            "flagged_records": len(flagged),
            "reviewed_and_signed": len(reviewed),
            "pending": len(flagged) - len(reviewed),
        },
        "contract": verdict.to_dict(),
        "recommendation": _recommendation(verdict),
    }
    block = _specificity_block(separation, specificity_states)
    if block is not None:
        result["strategy_specificity"] = block
    return result


def _regression_checks() -> dict:
    invariants = sc.registry_invariants()
    return {
        "registry_total": invariants["total"],
        "registry_conclusion_eligible": invariants["conclusion_eligible"],
        "b6_flag": {"env_var": b6.FLAG_ENV_VAR, "enabled": b6.flag_enabled(),
                    "state": b6.flag_state()},
        "candidate_classes": {
            spec.concept_id: sc.concept_metadata(spec.concept_id).get("class")
            for spec in CANDIDATES
        },
        "note": (
            "computed values above; file-level provenance (no detector, B2-B6, "
            "legacy or Ground-Truth change) is verified by the batch's test run "
            "and git status, not by this harness"
        ),
    }


def main() -> int:
    _load_mapping()

    native_identity, native_records = _native_records()
    benchmark_identity, benchmark_records = _benchmark_records()
    corpora = {"native": native_records, "benchmark": benchmark_records}

    reviews = _normalise_reviews(OUT_REVIEW)

    results = [
        _measure_candidate(spec, corpora, reviews) for spec in CANDIDATES
    ]

    if not OUT_REVIEW.exists():
        _write_review_template([
            {
                "record_id": record_id, "corpus": corpus,
                "candidate": result["concept"], "state": "PRESENT",
            }
            for result in results
            for corpus, data in result["measurements"].items()
            for record_id in data["shadow_only_ids"]
        ])

    payload = {
        "batch": "B10",
        "layer": "strategy-specificity contract + precision harness (evidence only)",
        "contract_version": sc.CONTRACT_VERSION,
        "analysis_versions": {
            "extractor": EXTRACTOR_VERSION,
            "relations": RELATIONS_VERSION,
        },
        "feature_flag": {
            "env_var": b6.FLAG_ENV_VAR,
            "enabled": b6.flag_enabled(),
            "state": b6.flag_state(),
        },
        "methodology": {
            "comparison": (
                "shadow B2 presence of the concept against the presence of its "
                "legacy namesake detector on the same submission"
            ),
            "legacy_is_not_an_oracle": (
                "legacy presence is a breadth-comparison axis only; a shadow_only "
                "record may be a legitimate improvement, a false detection, a "
                "representation difference or unresolved ambiguity"
            ),
            "review": (
                "every shadow_only record requires a signed human review entry "
                "in results/strategy_specificity_review.md before C3 can pass"
            ),
            "promotion": (
                "none; the harness produces evidence and never approves a change"
            ),
        },
        "corpora": {"native": native_identity, "benchmark": benchmark_identity},
        "review_file": str(OUT_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "regression_checks": _regression_checks(),
        "candidates": results,
        "totals": {
            "candidates": len(results),
            "unsafe": sum(1 for r in results if r["recommendation"] == UNSAFE),
            "safe": sum(1 for r in results if r["recommendation"] == SAFE),
            "unknown": sum(1 for r in results if r["recommendation"] == UNKNOWN),
            "shadow_only_records": sum(
                r["review"]["flagged_records"] for r in results
            ),
            "reviewed_and_signed": sum(
                r["review"]["reviewed_and_signed"] for r in results
            ),
            "promoted": 0,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("=" * 74)
    print("B10 strategy-specificity measurement | flag:", b6.flag_state())
    for result in results:
        counts = result["measurements"]
        print(f"  {result['concept']:26s} recommendation={result['recommendation']:8s} "
              f"verdict={result['contract']['verdict']}")
        for corpus, data in counts.items():
            print(f"      {corpus:10s} both={data['counts']['both']:3d} "
                  f"shadow_only={data['counts']['shadow_only']:3d} "
                  f"legacy_only={data['counts']['legacy_only']:3d} "
                  f"neither={data['counts']['neither']:3d} "
                  f"| legacy_evidence_only={data['legacy_evidence_only']:3d}")
        print(f"      failing clauses: {result['contract']['failing_clauses']}")
        block = result.get("strategy_specificity")
        if block:
            separated = block["key_origin_separation"]
            print(f"      B11 specificity: {block['states']} | "
                  f"eligible={len(separated['positive_records'])} "
                  f"refused={len(separated['negative_records'])} "
                  f"over_covered={len(separated['misclassified'])}")
            print(f"      B11 refused: {separated['negative_records']}")
    print("  promoted: 0  (this batch promotes nothing)")
    print("written:", OUT_JSON.relative_to(ROOT))
    print("review :", OUT_REVIEW.relative_to(ROOT))
    if not reviews:
        print("  review file was created: every shadow_only record is pending "
              "human review, so C3 stays blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
