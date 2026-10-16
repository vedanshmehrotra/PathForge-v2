"""Deterministic practice choices from catalog metadata and recorded exposure.

No detector, ground-truth, verdict, Elo, gap or Shadow input is consumed here.
Catalog topics describe the bank; they are not verified solution requirements.
"""

from collections import Counter

from pathforge.recommendation_links import problem_url

POLICY = "recorded_practice_v1"
HISTORY_LIMIT = 1000
DIFFICULTIES = ("Easy", "Medium", "Hard")


def _identity(value):
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _topics(value):
    # problems.topics is stored as comma-separated source tags, not patterns.
    values = value.split(",") if isinstance(value, str) else value if isinstance(value, list) else []
    return tuple(dict.fromkeys(v.strip() for v in values if isinstance(v, str) and v.strip()))


def recommend_practice(problems, history, *, difficulty=None, excluded_ids=(), limit=5):
    """History is newest first. Repeated analyses count as one exposure per URL.

    Prefer problems outside the history window, balancing listed topic exposure.
    Offer one older revisit when at least two different problems were recorded.
    The latest problem is withheld until another is recorded. This is a
    transparent choice heuristic, not a learning model.
    """
    if difficulty is not None and difficulty not in DIFFICULTIES:
        raise ValueError("Unsupported difficulty")
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("Choose between one and five suggestions")
    candidates, identities, conflicts = {}, {}, set()
    for p in problems:
        pid, url = _identity(p.get("id")), problem_url(p.get("link"))
        if not pid or not url:
            continue
        if pid in identities and identities[pid] != url:
            conflicts.add(pid)
        identities[pid] = url
        if (not isinstance(p.get("title"), str) or not p["title"].strip()
                or p.get("difficulty") not in DIFFICULTIES):
            continue
        candidates.setdefault(url, {"problem_id": pid, "title": p["title"].strip(),
                                   "difficulty": p["difficulty"], "problem_url": url,
                                   "topics": _topics(p.get("topics"))})
    for pid in conflicts:
        identities.pop(pid, None)
    candidates = {url: p for url, p in candidates.items() if p["problem_id"] not in conflicts}

    recorded, unmapped = {}, 0
    for row in history[:HISTORY_LIMIT]:
        url = identities.get(_identity(row.get("problem_id")))
        if url is None:
            unmapped += 1
        else:
            recorded.setdefault(url, len(recorded))
    exposure = Counter()
    for url in recorded:
        if url in candidates:
            exposure.update(topic.casefold() for topic in candidates[url]["topics"])

    excluded_urls = {identities[pid] for value in excluded_ids
                     if (pid := _identity(value)) in identities}
    matching = [p for url, p in candidates.items()
                if (difficulty is None or p["difficulty"] == difficulty)]
    available = [p for p in matching if p["problem_url"] not in excluded_urls]
    unseen = [p for p in available if p["problem_url"] not in recorded]
    # Never turn a just-submitted solution into an immediate practice assignment.
    revisits = sorted((p for p in available if recorded.get(p["problem_url"], 0) > 0),
                      key=lambda p: -recorded[p["problem_url"]])
    chosen, selected_topics = [], Counter()
    while unseen and len(chosen) < limit:
        def rank(p):
            topics = [t.casefold() for t in p["topics"]]
            return (sum(selected_topics[t] for t in topics),
                    min((exposure[t] for t in topics), default=0),
                    DIFFICULTIES.index(p["difficulty"]), p["problem_id"])
        item = min(unseen, key=rank)
        unseen.remove(item)
        chosen.append((item, "explore"))
        selected_topics.update(t.casefold() for t in item["topics"])
        if len(chosen) == min(2, limit - 1) and revisits:
            chosen.append((revisits.pop(0), "revisit"))
    while revisits and len(chosen) < limit:
        chosen.append((revisits.pop(0), "revisit"))

    recommendations = []
    for p, kind in chosen:
        reason = ("Revisit a previously recorded problem; it is older than your latest recorded problem."
                  if kind == "revisit" else
                  "Try a problem outside your recent recorded practice."
                  if recorded else "A starting choice from the current problem bank.")
        recommendations.append({**p, "topics": list(p["topics"]), "practice_kind": kind,
                                "reason": reason, "pattern": "", "score": None})
    state = ("available" if recommendations else "no_candidates" if not matching
             else "session_exhausted" if not available else "caught_up")
    return {"policy": POLICY, "state": state, "recommendations": recommendations,
            "history": {"scope": "latest_recorded_submissions", "limit": HISTORY_LIMIT,
                        "truncated": len(history) > HISTORY_LIMIT,
                        "mapped_problems": len(recorded), "unmapped_submissions": unmapped},
            "limitations": ["Recorded practice does not establish correctness or mastery.",
                            "Catalog topics are descriptive; solution requirements are not inferred."],
            "summary": {"primary_weak_patterns": [], "focus_area": "",
                        "recommendation_strategy": POLICY}}
