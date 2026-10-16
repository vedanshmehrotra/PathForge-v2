"""Phase 4-HR — human-review transcript, verification, and label overlay.

This module is the ONLY new input path introduced by the post-human-review run.
It does not change the frozen grouping, labeling, derivation, control or
validation logic: it translates the reviewer's per-family decisions into a
label artifact of exactly the shape ``labeling.build()`` produces, and the
existing ``derive.derive(..., label_mode=LABEL_MODE_STRICT)`` then consumes it
unchanged.

Interpretation contract
-----------------------
* ``human_review.json`` is the authoritative, committed transcript of the
  reviewer's decisions (see its ``sources`` block for the raw PDF digests and
  the mechanical extraction commands).  The pipeline reads only the transcript,
  never the PDFs, so the run stays deterministic and dependency-free.
* A ``CORRECTED_LABEL`` decision is a human-approved family label: the reviewer
  replaced a label the POC could not supply.  It is therefore mapped to
  ``approval_state = "APPROVED"`` (the state strict derivation activates) while
  ``human_decision`` keeps the ``APPROVED`` / ``CORRECTED_LABEL`` distinction in
  the audit trail.  No new activation state is introduced.
* A ``REJECTED`` decision is never activatable.
* A corrected label is NOT added to the runtime vocabulary.  Its terms are fed
  to ``required`` as-is, so a term the frozen taxonomy does not register is
  reported as a vocabulary gap and the family resolves to
  ``LABEL_UNEXPRESSIBLE`` (no group) by the existing state machine.  Nothing is
  invented to make such a label expressible.

Blinding is preserved: the reviewer saw only the blind sheet, and this module
never feeds analyzer detections back into a label.
"""
import hashlib
import json
import os
import re

from .labeling import divergence_state
from .problem_metadata import PEC_CONCEPTS, SUPPORT_TECHNIQUES

HERE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT_PATH = os.path.join(HERE, "human_review.json")
MARKDOWN_PATH = os.path.join(HERE, "human_review.md")
EXTRACTED_DECISIONS = os.path.join(HERE, "human_review_source.txt")
EXTRACTED_SOLUTIONS = os.path.join(HERE, "human_review_solutions_source.txt")

DECISION_APPROVED = "APPROVED"
DECISION_CORRECTED = "CORRECTED_LABEL"
DECISION_REJECTED = "REJECTED"

APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"
APPROVAL_PENDING = "PENDING_REVIEW"

#: reviewer decision -> the approval state the frozen derivation activates on.
DECISION_TO_APPROVAL = {
    DECISION_APPROVED: APPROVAL_APPROVED,
    DECISION_CORRECTED: APPROVAL_APPROVED,
    DECISION_REJECTED: APPROVAL_REJECTED,
}

_FAMILY_KEY_RE = re.compile(r"lc\d+_fam\d+")
_SUMMARY_RE = re.compile(
    r"APPROVED:\s*(\d+)\s*\|\s*CORRECTED LABEL:\s*(\d+)\s*\|\s*REJECTED:\s*(\d+)"
)
_DECISION_LINE_RE = re.compile(
    r"lc\d+_fam\d+\s*--\s*(APPROVED|CORRECTED LABEL|REJECTED)\s*(.*)$"
)
_LABEL_TOKEN_RE = re.compile(
    r"[A-Za-z_][A-Za-z_0-9]*(?:\s*\+\s*[A-Za-z_][A-Za-z_0-9]*)*"
    r"(?:\s*\([A-Za-z][A-Za-z\-]*\))?"
)


def sha256_file(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load() -> dict:
    """Load the committed transcript."""
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Verification: the transcript must agree with the raw reviewer artifacts.
# ---------------------------------------------------------------------------

def _parse_decisions_from_solutions_text(text: str) -> dict:
    """Per-family decision parsed from the reviewer-facing solutions sheet.

    Each reference implementation carries a docstring header of the form
    ``lc<N>_fam<M> -- APPROVED (label)`` / ``-- CORRECTED LABEL: label`` /
    ``-- REJECTED``.  That is a mechanical per-family record of the reviewer's
    decision and is used to cross-check the transcript.
    """
    lines = text.splitlines()
    found = {}
    for idx, line in enumerate(lines):
        m = _DECISION_LINE_RE.search(line)
        if not m:
            continue
        key_match = _FAMILY_KEY_RE.search(line)
        if key_match is None:
            continue
        decision = "CORRECTED_LABEL" if m.group(1) == "CORRECTED LABEL" else m.group(1)
        rest = m.group(2).strip()
        label = None
        if rest.startswith(":"):
            rest = rest[1:].strip()
        elif rest.startswith("("):
            label = rest[1:].split(")")[0].strip()
            rest = ""
        elif rest.startswith("--"):
            rest = ""
        if label is None and rest:
            tok = _LABEL_TOKEN_RE.match(rest)
            label = tok.group(0).strip() if tok else None
        if label is None:
            # label wrapped onto the following line (e.g. "CORRECTED LABEL:\ndp_bottom_up")
            for nxt in lines[idx + 1: idx + 3]:
                nxt = nxt.strip()
                if not nxt:
                    continue
                tok = _LABEL_TOKEN_RE.match(nxt)
                label = tok.group(0).strip() if tok else None
                break
        found[key_match.group(0)] = {"decision": decision, "label": label}
    return found


def verify(transcript: dict, families_artifact: dict) -> dict:
    """Cross-check the transcript against the raw sources and the family set."""
    decisions = transcript["decisions"]
    by_key = {d["family_key"]: d for d in decisions}
    family_keys = {f["family_key"] for f in families_artifact["families"]}

    tally = {DECISION_APPROVED: 0, DECISION_CORRECTED: 0, DECISION_REJECTED: 0}
    for d in decisions:
        tally[d["human_decision"]] = tally.get(d["human_decision"], 0) + 1

    declared = transcript["summary"]
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    add("decision_count", len(decisions) == len(family_keys),
        f"{len(decisions)} decisions for {len(family_keys)} families")
    add("unique_family_keys", len(by_key) == len(decisions),
        f"{len(by_key)} unique of {len(decisions)}")
    add("coverage_bijective", set(by_key) == family_keys,
        f"unreviewed={sorted(family_keys - set(by_key))} "
        f"unknown={sorted(set(by_key) - family_keys)}")
    add("tally_matches_summary",
        tally[DECISION_APPROVED] == declared["approved"]
        and tally[DECISION_CORRECTED] == declared["corrected_label"]
        and tally[DECISION_REJECTED] == declared["rejected"],
        f"transcript={tally} summary={declared}")
    add("reviewer_reason_recorded",
        all(d.get("reviewer_reason") for d in decisions),
        "every decision carries a reviewer reason")
    add("source_ref_recorded",
        all(d.get("source_ref") for d in decisions),
        "every decision carries a source reference")
    add("review_status_recorded",
        all(d.get("review_status") for d in decisions),
        "every decision carries a review status")
    add("label_terms_recorded",
        all((d["human_label_terms"] or d["human_decision"] == DECISION_REJECTED)
            for d in decisions),
        "every non-rejected decision has label terms")
    add("no_vocabulary_invention",
        all(t not in ("", None) for d in decisions for t in d["human_label_terms"]),
        "label terms are non-empty identifiers")

    # ---- source digests (trail only: missing raw file is reported, not fatal)
    source_status = []
    for name, spec in transcript["sources"].items():
        path = os.path.join(HERE, spec["path"])
        observed = sha256_file(path)
        expected = spec.get("sha256")
        if observed is None:
            state = "source_missing"
        elif expected is None:
            state = "recorded_by_extraction"
        elif observed == expected:
            state = "verified"
        else:
            state = "mismatch"
        source_status.append({
            "name": name, "path": spec["path"], "role": spec.get("role", ""),
            "expected_sha256": expected, "observed_sha256": observed,
            "state": state,
        })
    add("source_digests_not_mismatched",
        all(s["state"] != "mismatch" for s in source_status),
        "; ".join(f"{s['name']}={s['state']}" for s in source_status))

    # ---- mechanical extraction cross-check
    extraction = {}
    if os.path.exists(EXTRACTED_DECISIONS):
        text = open(EXTRACTED_DECISIONS, encoding="utf-8").read()
        keys = set(_FAMILY_KEY_RE.findall(text))
        m = _SUMMARY_RE.search(text)
        extraction["decisions_txt_family_keys"] = len(keys)
        extraction["decisions_txt_summary"] = list(m.groups()) if m else None
        add("extraction_family_keys_match", keys == family_keys,
            f"decisions pdf mentions {len(keys)} family keys")
        add("extraction_summary_match",
            m is not None and tuple(int(x) for x in m.groups())
            == (declared["approved"], declared["corrected_label"], declared["rejected"]),
            f"summary line {extraction['decisions_txt_summary']} vs {declared}")
    else:
        extraction["decisions_txt_family_keys"] = None
        extraction["decisions_txt_summary"] = None

    if os.path.exists(EXTRACTED_SOLUTIONS):
        parsed = _parse_decisions_from_solutions_text(
            open(EXTRACTED_SOLUTIONS, encoding="utf-8").read())
        extraction["solutions_txt_decisions_parsed"] = len(parsed)
        mismatched = []
        for key, got in sorted(parsed.items()):
            want = by_key.get(key)
            if want is None:
                mismatched.append({"family_key": key, "issue": "not_in_transcript"})
                continue
            if got["decision"] != want["human_decision"]:
                mismatched.append({"family_key": key, "issue": "decision",
                                   "sheet": got["decision"],
                                   "transcript": want["human_decision"]})
        add("extraction_decisions_match",
            set(parsed) == family_keys and not mismatched,
            f"parsed {len(parsed)} per-family decisions from the reviewer sheet; "
            f"mismatches={mismatched}")

        label_mismatch = []
        for key, got in sorted(parsed.items()):
            want = by_key.get(key)
            if want is None or want["human_decision"] == DECISION_REJECTED:
                continue
            sheet_label = (got["label"] or "").strip()
            transcript_label = (want["corrected_label"] or want["human_label"] or "").strip()
            if sheet_label and sheet_label != transcript_label:
                label_mismatch.append({"family_key": key, "sheet": sheet_label,
                                       "transcript": transcript_label})
        add("extraction_labels_match", not label_mismatch,
            f"label mismatches between reviewer sheet and transcript: {label_mismatch}")
    else:
        extraction["solutions_txt_decisions_parsed"] = None

    return {
        "checks": checks,
        "passed": all(c["passed"] for c in checks),
        "failed_checks": [c["check"] for c in checks if not c["passed"]],
        "tally": tally,
        "declared_summary": declared,
        "member_total": sum(f["member_count"] for f in families_artifact["families"]),
        "source_status": source_status,
        "extraction": extraction,
    }


# ---------------------------------------------------------------------------
# Overlay: transcript -> label artifact of the frozen shape
# ---------------------------------------------------------------------------

def _tier_of(rows: dict, fam: dict, concept: str) -> str:
    for sid in fam["members"]:
        tier = rows[sid]["concept_tiers"].get(concept)
        if tier:
            return tier
    return "SUPPORT"


def _observed(rows: dict, members: list):
    sets = [set(rows[m]["concepts"]) for m in members]
    union = set().union(*sets) if sets else set()
    inter = set.intersection(*sets) if sets else set()
    return sorted(union), sorted(inter)


def unregistered_terms(terms: list) -> list:
    """Label terms the frozen taxonomy does not register (vocabulary gap)."""
    return sorted(t for t in terms if t not in PEC_CONCEPTS and t not in SUPPORT_TECHNIQUES)


def overlay(reference_artifact: dict, normalized_artifact: dict, group_artifact: dict,
            label_artifact: dict, transcript: dict) -> tuple:
    """Apply the human review to the label artifact.

    Returns ``(post_review_labels, overlay_audit)``.  The post-review artifact
    has exactly the shape ``derive.derive()`` expects; the audit records the
    before/after state of every family.
    """
    rows = {r["solution_id"]: r for r in normalized_artifact["solutions"]}
    families = {f["family_key"]: f for f in group_artifact["families"]}
    decisions = {d["family_key"]: d for d in transcript["decisions"]}

    entries = []
    audit_rows = []
    gaps = {}

    for entry in label_artifact["entries"]:
        key = entry["family_key"]
        fam = families[key]
        d = decisions[key]
        new = json.loads(json.dumps(entry))  # deep copy; source artifact untouched

        observed_union, observed_intersection = _observed(rows, fam["members"])
        terms = sorted(d["human_label_terms"])
        approval_state = DECISION_TO_APPROVAL[d["human_decision"]]
        origin = ("approved_as_proposed" if d["human_decision"] == DECISION_APPROVED
                  else ("human_corrected" if d["human_decision"] == DECISION_CORRECTED
                        else "human_rejected"))
        unreg = unregistered_terms(terms)
        for term in unreg:
            gaps.setdefault(term, []).append(key)

        before_required = list(entry["proposed_label"]["required"])
        before_state = entry["divergence_state"]

        new["approval_state"] = approval_state
        new["approval_state_detail"] = (
            "human review: " + d["human_decision"]
        )
        new["human_decision"] = d["human_decision"]
        new["human_label"] = d["human_label"]
        new["human_corrected_label"] = d["corrected_label"]
        new["human_qualifier"] = d["qualifier"]
        new["human_label_terms"] = terms
        new["reviewer"] = transcript["reviewer"]
        new["reviewer_notes"] = d["reviewer_reason"]
        new["review_source_ref"] = d["source_ref"]
        new["review_status"] = d["review_status"]
        new["approved"] = (approval_state == APPROVAL_APPROVED)
        new["label_origin"] = origin
        new["unregistered_label_terms"] = unreg
        new["vocabulary_gap"] = bool(unreg)

        # Human labels do not carry a reviewer-authored exclusion set; a
        # problem-level `excluded` set must not be attributed to a family the
        # reviewer labelled independently.
        excluded = []
        new["proposed_label"] = {
            "label_source": "human_review",
            "label_source_detail": (
                f"{transcript['reviewer']}: {d['human_decision']} "
                f"({d['source_ref']})"
            ),
            "granularity": "family_level_human_approved",
            "problem_patterns": entry["proposed_label"]["problem_patterns"],
            "required": terms,
            "optional": [],
            "excluded": excluded,
            "required_expected": sorted(c for c in terms if c not in observed_union),
            "rationale": d["reviewer_reason"],
        }
        new["divergence_state"] = divergence_state(
            terms, observed_intersection, lambda c: _tier_of(rows, fam, c),
            bool(fam["zero_evidence"]),
        )

        entries.append(new)
        audit_rows.append({
            "family_key": key,
            "problem_id": fam["problem_id"],
            "member_count": fam["member_count"],
            "human_decision": d["human_decision"],
            "approval_state": approval_state,
            "label_origin": origin,
            "human_label": d["human_label"],
            "human_corrected_label": d["corrected_label"],
            "qualifier": d["qualifier"],
            "human_label_terms": terms,
            "unregistered_label_terms": unreg,
            "vocabulary_gap": bool(unreg),
            "before": {
                "proposed_required": before_required,
                "proposed_label_source": entry["proposed_label"]["label_source"],
                "divergence_state": before_state,
                "approval_state": entry["approval_state"],
            },
            "after": {
                "required": terms,
                "divergence_state": new["divergence_state"],
                "activation_eligible": approval_state == APPROVAL_APPROVED,
            },
            "observed_intersection": observed_intersection,
            "observed_union": observed_union,
            "zero_evidence": bool(fam["zero_evidence"]),
            "reviewer_reason": d["reviewer_reason"],
            "source_ref": d["source_ref"],
        })

    states = {}
    for e in entries:
        states[e["divergence_state"]] = states.get(e["divergence_state"], 0) + 1
    approvals = {}
    for e in entries:
        approvals[e["approval_state"]] = approvals.get(e["approval_state"], 0) + 1

    approved_as_proposed = sum(1 for e in entries if e["label_origin"] == "approved_as_proposed")
    approved_corrected = sum(1 for e in entries if e["label_origin"] == "human_corrected")
    rejected = sum(1 for e in entries if e["label_origin"] == "human_rejected")

    post = {
        "phase": "4_family_labeling_post_human_review",
        "label_source": "human_review",
        "reviewer": transcript["reviewer"],
        "review_round": transcript["round"],
        "independence_rule": (
            "labels are the reviewer's family-level decisions; the analyzer's "
            "detections never author a label"
        ),
        "analyzer_detection_visible_to_reviewer": False,
        "auto_approval": False,
        "approval_state_semantics": (
            "approval_state=APPROVED covers both APPROVED and CORRECTED_LABEL "
            "reviewer decisions (both are human-approved family labels); the "
            "distinction is preserved in human_decision / label_origin. "
            "REJECTED is never activatable."
        ),
        "corrected_labels_added_to_runtime_vocabulary": False,
        "totals": {
            "families": len(entries),
            "approval_states": approvals,
            "approved": approved_as_proposed + approved_corrected,
            "approved_as_proposed": approved_as_proposed,
            "approved_corrected": approved_corrected,
            "rejected": rejected,
            "divergence_state_counts": states,
        },
        "entries": entries,
    }

    audit = {
        "phase": "4_hr_overlay_audit",
        "reviewer": transcript["reviewer"],
        "round": transcript["round"],
        "totals": post["totals"],
        "vocabulary_gaps": {k: sorted(v) for k, v in sorted(gaps.items())},
        "vocabulary_gap_family_count": len({f for v in gaps.values() for f in v}),
        "families": audit_rows,
    }
    return post, audit


def render_markdown(transcript: dict, verification: dict, audit: dict) -> str:
    s = transcript["summary"]
    lines = [
        "# Ground-Truth POC V2 — Human Review (Round 1)",
        "",
        f"- **reviewer:** {transcript['reviewer']}",
        f"- **mode:** {transcript['review_mode']} (analyzer detections were NOT shown)",
        f"- **status:** {transcript['status']}",
        f"- **scope:** {transcript['scope']}",
        "",
        "## Summary",
        "",
        f"- reviewed families: **{s['reviewed_families']}**",
        f"- APPROVED: **{s['approved']}**",
        f"- CORRECTED LABEL: **{s['corrected_label']}**",
        f"- REJECTED: **{s['rejected']}**",
        "",
        "## Source provenance",
        "",
        "| artifact | sha256 | role |",
        "|---|---|---|",
    ]
    for name, spec in transcript["sources"].items():
        lines.append(f"| `{spec['path']}` | `{spec.get('sha256') or '—'}` | {spec.get('role','')} |")
    lines += [
        "",
        "Raw reviewer PDFs are never modified. `human_review_source.txt` / "
        "`human_review_solutions_source.txt` are mechanical `pdftotext` "
        "extractions used only for verification.",
        "",
        "## Transcript verification",
        "",
        f"- passed: **{verification['passed']}**",
        f"- failed checks: {verification['failed_checks'] or 'none'}",
        "",
        "| check | passed | detail |",
        "|---|---|---|",
    ]
    for c in verification["checks"]:
        lines.append(f"| `{c['check']}` | {'yes' if c['passed'] else 'NO'} | {c['detail']} |")
    lines += [
        "",
        "## Reviewer remarks",
        "",
    ]
    for r in transcript["reviewer_general_remarks"]:
        lines.append(f"- {r}")
    lines += [
        "",
        "## Family-level decisions",
        "",
        "| family | n | decision | human label | approved label terms | "
        "before (POC proposed) | after (divergence state) | vocabulary gap |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in audit["families"]:
        before = ", ".join(row["before"]["proposed_required"]) or "_(no label)_"
        lines.append(
            f"| `{row['family_key']}` | {row['member_count']} | {row['human_decision']} | "
            f"{row['human_label'] or '_(rejected)_'} | "
            f"{', '.join(row['human_label_terms']) or '—'} | {before} | "
            f"`{row['after']['divergence_state']}` | "
            f"{', '.join(row['unregistered_label_terms']) or '—'} |"
        )
    lines += [
        "",
        "## Vocabulary gaps (human label terms the frozen taxonomy does not register)",
        "",
    ]
    if audit["vocabulary_gaps"]:
        for term, fams in audit["vocabulary_gaps"].items():
            lines.append(f"- `{term}` — {len(fams)} family/families: {', '.join(fams)}")
    else:
        lines.append("- none")
    lines += [
        "",
        "No corrected label has been added to the runtime vocabulary. Each gap "
        "above is a taxonomy candidate only (see the post-human-review report).",
        "",
    ]
    return "\n".join(lines)


def run(families_artifact: dict, reference_artifact: dict,
        normalized_artifact: dict, label_artifact: dict, write: bool = True) -> dict:
    transcript = load()
    verification = verify(transcript, families_artifact)
    post, audit = overlay(reference_artifact, normalized_artifact,
                          families_artifact, label_artifact, transcript)
    markdown = render_markdown(transcript, verification, audit)
    if write:
        with open(MARKDOWN_PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(markdown)
    return {
        "transcript": transcript,
        "verification": verification,
        "labels": post,
        "audit": audit,
        "markdown": markdown,
        "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
    }
