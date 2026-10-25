"""Calendar-aware practice choices. Exposure and catalog topics are not skill labels."""

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import json

from pathforge.practice_recommendations import DIFFICULTIES, HISTORY_LIMIT, _identity, _topics
from pathforge.recommendation_links import problem_url

POLICY = "calendar_practice_v2"
RETURN_INTERVAL = timedelta(days=7)
# Only recognized algorithm topics can justify a targeted link. Broad source
# tags (including Math/Hash Table) and unknown metadata remain general choices.
TARGET_TOPICS = frozenset({"binary search", "sliding window", "two pointers", "stack",
    "monotonic stack", "monotonic queue", "dynamic programming", "backtracking",
    "depth-first search", "breadth-first search", "union find", "trie", "prefix sum",
    "heap (priority queue)", "shortest path", "topological sort", "segment tree",
    "binary indexed tree", "divide and conquer", "bit manipulation", "greedy"})


def _source_topics(value):
    if isinstance(value, str) and value.lstrip().startswith("["):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return ()
    return _topics(value)


def _catalog(rows):
    aliases, identities, conflicts, paid_urls = {}, {}, set(), set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        pid, url = _identity(row.get("id")), problem_url(row.get("link"))
        if not pid or not url:
            continue
        if row.get("premium_only") is True:
            paid_urls.add(url)
        if pid in identities and identities[pid] != url:
            conflicts.add(pid)
        identities[pid] = url
        title, difficulty = row.get("title"), row.get("difficulty")
        if not isinstance(title, str) or not title.strip() or difficulty not in DIFFICULTIES:
            continue
        tags = {t.casefold(): t for t in sorted(_source_topics(row.get("topics")))}
        aliases.setdefault(url, []).append((pid, title.strip(), difficulty, tags))

    items, mapping = {}, {}
    for url, definitions in aliases.items():
        if url in paid_urls:
            continue
        definitions = [d for d in definitions if d[0] not in conflicts]
        signatures = {(d[1].casefold(), d[2], tuple(sorted(d[3]))) for d in definitions}
        if len(signatures) != 1:
            continue
        pid, title, difficulty, tags = min(definitions, key=lambda d: d[0])
        items[url] = {"problem_id": pid, "title": title, "difficulty": difficulty,
                      "problem_url": url, "topics": [tags[t] for t in sorted(tags)]}
        for definition in definitions:
            mapping[definition[0]] = url
    return items, mapping


def _timestamp(value, now):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.utcoffset() is None or value > now:
        return None
    try:
        return value.astimezone(timezone.utc)
    except OverflowError:
        return None


def recommend_calendar_practice(problems, history, *, now, difficulty=None, excluded_ids=(),
                               focus_slug=None, allow_explore=True):
    """Newest-first bounded history; no writes, online inference or outcome labels.

    O(N*T + H log H + H*T + 3*N*T), with at most 1,000 distinct problems.
    Dates/day deduplication use UTC. Seven elapsed days is a scheduling heuristic.
    """
    if not isinstance(history, list):
        raise ValueError("An explicit history list is required")
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        raise ValueError("Unsupported difficulty")
    now = now.astimezone(timezone.utc)
    items, mapping = _catalog(problems)
    focus_url = problem_url(f"https://leetcode.com/problems/{focus_slug}/") if focus_slug else None
    if focus_slug and focus_url not in items:
        return {"policy": POLICY, "state": "context_unavailable", "recommendations": [],
                "context": {"related_available": False},
                "limitations": ["The current problem is not available in the practice catalog."]}
    tags = {url: {t.casefold() for t in item["topics"]} for url, item in items.items()}
    specific = {url: values & TARGET_TOPICS for url, values in tags.items()}
    seen, dated, invalid_urls = set(), {}, set()
    invalid, unmapped, first_url = 0, 0, None
    for row in history[:HISTORY_LIMIT]:
        url = mapping.get(_identity(row.get("problem_id"))) if isinstance(row, Mapping) else None
        if not url:
            unmapped += 1
            continue
        first_url = first_url or url
        seen.add(url)
        timestamp = _timestamp(row.get("submitted_at"), now)
        if timestamp is None:
            invalid += 1
            invalid_urls.add(url)
            continue
        key = (url, timestamp.date())
        dated[key] = max(timestamp, dated.get(key, timestamp))

    # Python's stable sort retains newest-first input order for equal times.
    ordered = sorted(((stamp, url) for (url, _), stamp in dated.items()), key=lambda row: row[0], reverse=True)
    latest = first_url if invalid else ordered[0][1] if ordered else first_url
    if focus_url:
        latest = focus_url
        seen.add(focus_url)
    last_problem, last_topic, exposure = {}, {}, Counter()
    unknown_topics = set().union(*(tags[url] for url in invalid_urls)) if invalid_urls else set()
    for stamp, url in ordered:
        last_problem.setdefault(url, stamp)
        for tag in tags[url]:
            last_topic.setdefault(tag, (stamp, url))
            exposure[tag] += 1 / len(tags[url])

    exclusions = {mapping.get(_identity(pid)) for pid in excluded_ids}
    preferred = items[latest]["difficulty"] if latest and (focus_url or latest not in invalid_urls) else "Easy"
    matching = [p for p in items.values() if (p["difficulty"] == difficulty if difficulty else
                DIFFICULTIES.index(p["difficulty"]) <= DIFFICULTIES.index(preferred))]
    available = [p for p in matching if p["problem_url"] not in exclusions]
    fresh = [p for p in available if p["problem_url"] not in seen]
    revisits = sorted((p for p in available if p["problem_url"] not in invalid_urls
                       and p["problem_url"] in last_problem
                       and now - last_problem[p["problem_url"]] >= RETURN_INTERVAL),
                      key=lambda p: (last_problem[p["problem_url"]], p["problem_url"]))
    selected, selected_topics = [], Counter()

    def rank(item):
        values = tags[item["problem_url"]]
        level = DIFFICULTIES.index(item["difficulty"])
        target = DIFFICULTIES.index(preferred)
        distance = (abs(level-target), level > target)
        return (not bool(values), sum(selected_topics[t] for t in values), distance,
                sum(exposure[t] for t in values) / max(1, len(values)), item["problem_url"])

    def add(item, kind, anchor=None, shared=()):
        url = item["problem_url"]
        result = {**item, "practice_kind": kind, "pattern": "", "score": None}
        if anchor:
            stamp, anchor_url = anchor
            anchor_item = items[anchor_url]
            display_tags = sorted(t for t in item["topics"] if t.casefold() in shared)
            result["reason_evidence"] = {"anchor_url": anchor_url, "anchor_title": anchor_item["title"],
                                         "shared_topics": display_tags}
            if stamp is not None:
                result["reason_evidence"]["anchor_date"] = stamp.date().isoformat()
            if kind == "revisit":
                reason = f"Revisit this problem, last recorded on {stamp.date().isoformat()}."
            else:
                reason = (f"Shares {', '.join(display_tags)} with {anchor_item['title']}" +
                          (f", recorded on {stamp.date().isoformat()}." if stamp is not None else "."))
        else:
            reason = ("A starting choice from the current problem bank." if kind == "starter" else
                      "A different choice from the current bank to vary your practice.")
        result["reason"] = reason
        selected.append(result)
        selected_topics.update(tags[url])
        if item in fresh:
            fresh.remove(item)
        if item in revisits:
            revisits.remove(item)

    # Use the actual latest exposure to a specific tag, not an arbitrary old event.
    due = {tag: (stamp, url) for tag, (stamp, url) in last_topic.items()
           if tag in TARGET_TOPICS and tag not in unknown_topics and now-stamp >= RETURN_INTERVAL}
    # Scan candidates once, rather than once per stale tag.
    returns = []
    for item in fresh:
        shared = specific[item["problem_url"]] & due.keys()
        if shared:
            tag = min(shared, key=lambda tag: (*due[tag], tag))
            stamp, url = due[tag]
            returns.append((stamp, url, tag, item))
    if returns and not focus_url:
        stamp, url, tag, item = min(returns, key=lambda r: (r[0], r[1], r[2], rank(r[3])))
        add(item, "related_return", (stamp, url), {tag})
    else:
        if revisits and not focus_url:
            item = revisits[0]
            add(item, "revisit", (last_problem[item["problem_url"]], item["problem_url"]))

    # A companion link promises a related catalog topic, never a diagnosed gap
    # or proof that another problem requires the detected algorithm. Hash Table
    # is useful in this explicit context; broad Array/String overlap is not.
    context_tags = tags[focus_url] & (TARGET_TOPICS | {"hash table"}) if focus_url else set()
    if latest and (focus_url or latest not in invalid_urls):
        related = [p for p in fresh if (tags[p["problem_url"]] & context_tags if focus_url else
                                       specific[p["problem_url"]] & specific[latest])]
        if related:
            item = min(related, key=rank)
            add(item, "follow_up", (last_problem.get(latest), latest),
                tags[item["problem_url"]] & context_tags if focus_url else specific[item["problem_url"]] & specific[latest])
    while fresh and len(selected) < 3:
        related = [p for p in fresh if tags[p["problem_url"]] & context_tags] if focus_url else []
        if related:
            item = min(related, key=rank)
            add(item, "follow_up", (last_problem.get(latest), latest), tags[item["problem_url"]] & context_tags)
        elif focus_url and not allow_explore:
            break
        else:
            add(min(fresh, key=rank), "explore" if history or focus_url else "starter")
    if not focus_url and revisits and len(selected) < 3 and not any(r["practice_kind"] == "revisit" for r in selected):
        item = revisits[0]
        add(item, "revisit", (last_problem[item["problem_url"]], item["problem_url"]))

    eligible_before_skips = [p for p in matching if p["problem_url"] not in seen or (
        p["problem_url"] not in invalid_urls and p["problem_url"] in last_problem
        and now-last_problem[p["problem_url"]] >= RETURN_INTERVAL)]
    state = ("available" if selected else "difficulty_limited" if items and not matching and difficulty is None else
             "no_candidates" if not matching else "session_exhausted" if eligible_before_skips else "caught_up")
    return {"policy": POLICY, "state": state, "recommendations": selected,
            "context": {"latest_problem_id": items[latest]["problem_id"] if latest else None,
                        "default_max_difficulty": preferred if difficulty is None else None,
                        **({"source_problem_url": focus_url,
                            "related_available": any(r["practice_kind"] == "follow_up" for r in selected)} if focus_url else {})},
            "history": {"scope": "latest_recorded_submissions", "limit": HISTORY_LIMIT,
                        "truncated": len(history) > HISTORY_LIMIT, "mapped_problems": len(seen),
                        "unmapped_submissions": unmapped, "invalid_timestamps": invalid,
                        "dated_exposures": len(dated), "calendar_timezone": "UTC"},
            "limitations": ["Recorded practice does not establish correctness or mastery.",
                            "Shared catalog topics do not prove the same algorithm is required.",
                            "Seven elapsed days is a scheduling heuristic, not predicted forgetting."],
            "summary": {"primary_weak_patterns": [], "focus_area": "", "recommendation_strategy": POLICY}}
