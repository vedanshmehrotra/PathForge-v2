"""Calendar-aware practice choices. Exposure and catalog topics are not skill labels."""

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from pathforge.practice_recommendations import DIFFICULTIES, HISTORY_LIMIT, _identity, _topics
from pathforge.recommendation_links import problem_url

POLICY = "calendar_practice_v2"
RETURN_INTERVAL = timedelta(days=7)
# A shared container/type alone is too broad to label a targeted follow-up.
# These tags still contribute to general variety, never to mastery estimates.
BROAD_TOPICS = frozenset({"array", "arrays", "string", "strings", "matrix", "matrices",
                          "linked list", "linked lists", "tree", "trees", "binary tree",
                          "binary trees", "graph", "graphs"})


def _catalog(rows):
    aliases, identities, conflicts = {}, {}, set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        pid, url = _identity(row.get("id")), problem_url(row.get("link"))
        if not pid or not url:
            continue
        if pid in identities and identities[pid] != url:
            conflicts.add(pid)
        identities[pid] = url
        title, difficulty = row.get("title"), row.get("difficulty")
        if not isinstance(title, str) or not title.strip() or difficulty not in DIFFICULTIES:
            continue
        tags = {t.casefold(): t for t in sorted(_topics(row.get("topics")))}
        aliases.setdefault(url, []).append((pid, title.strip(), difficulty, tags))

    items, mapping = {}, {}
    for url, definitions in aliases.items():
        definitions = [d for d in definitions if d[0] not in conflicts]
        signatures = {(d[1], d[2], tuple(sorted(d[3]))) for d in definitions}
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


def recommend_calendar_practice(problems, history, *, now, difficulty=None, excluded_ids=()):
    """Newest-first bounded history; no writes, online inference or outcome labels.

    O(N*T + H log H + H*T + 3*N*T), with at most 1,000 history rows.
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
    tags = {url: {t.casefold() for t in item["topics"]} for url, item in items.items()}
    specific = {url: values - BROAD_TOPICS for url, values in tags.items()}
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

    ordered = sorted(((stamp, url) for (url, _), stamp in dated.items()), reverse=True)
    latest = first_url if invalid else ordered[0][1] if ordered else first_url
    last_problem, last_topic, exposure = {}, {}, Counter()
    unknown_topics = set().union(*(tags[url] for url in invalid_urls)) if invalid_urls else set()
    for stamp, url in ordered:
        last_problem.setdefault(url, stamp)
        for tag in tags[url]:
            last_topic.setdefault(tag, (stamp, url))
            exposure[tag] += 1 / len(tags[url])

    exclusions = {mapping.get(_identity(pid)) for pid in excluded_ids}
    matching = [p for p in items.values() if difficulty is None or p["difficulty"] == difficulty]
    available = [p for p in matching if p["problem_url"] not in exclusions]
    fresh = [p for p in available if p["problem_url"] not in seen]
    revisits = sorted((p for p in available if p["problem_url"] != latest
                       and p["problem_url"] not in invalid_urls
                       and p["problem_url"] in last_problem
                       and now - last_problem[p["problem_url"]] >= RETURN_INTERVAL),
                      key=lambda p: (last_problem[p["problem_url"]], p["problem_url"]))
    preferred = items[latest]["difficulty"] if latest and latest not in invalid_urls else "Easy"
    selected, selected_topics = [], Counter()

    def rank(item):
        values = tags[item["problem_url"]]
        level = DIFFICULTIES.index(item["difficulty"])
        target = DIFFICULTIES.index(preferred)
        distance = (abs(level-target), level > target)
        return (sum(selected_topics[t] for t in values), distance,
                sum(exposure[t] for t in values) / max(1, len(values)), item["problem_url"])

    def add(item, kind, anchor=None, shared=()):
        url = item["problem_url"]
        result = {**item, "practice_kind": kind, "pattern": "", "score": None}
        if anchor:
            stamp, anchor_url = anchor
            anchor_item = items[anchor_url]
            display_tags = sorted(t for t in item["topics"] if t.casefold() in shared)
            result["reason_evidence"] = {"anchor_url": anchor_url, "anchor_title": anchor_item["title"],
                                         "anchor_date": stamp.date().isoformat(), "shared_topics": display_tags}
            if kind == "revisit":
                reason = f"Revisit this problem, last recorded on {stamp.date().isoformat()}."
            else:
                reason = f"Shares {', '.join(display_tags)} with {anchor_item['title']}, recorded on {stamp.date().isoformat()}."
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
    due = sorted((stamp, url, tag) for tag, (stamp, url) in last_topic.items()
                 if tag not in BROAD_TOPICS and tag not in unknown_topics and now-stamp >= RETURN_INTERVAL)
    for stamp, url, tag in due:
        related = [p for p in fresh if tag in specific[p["problem_url"]]]
        if related:
            add(min(related, key=rank), "related_return", (stamp, url), {tag})
            break
    else:
        if revisits:
            item = revisits[0]
            add(item, "revisit", (last_problem[item["problem_url"]], item["problem_url"]))

    if latest and latest not in invalid_urls:
        related = [p for p in fresh if specific[p["problem_url"]] & specific[latest]]
        if related:
            item = min(related, key=rank)
            add(item, "follow_up", (last_problem[latest], latest), specific[item["problem_url"]] & specific[latest])
    while fresh and len(selected) < 3:
        add(min(fresh, key=rank), "explore" if history else "starter")
    while revisits and len(selected) < 3:
        item = revisits[0]
        add(item, "revisit", (last_problem[item["problem_url"]], item["problem_url"]))

    state = ("available" if selected else "no_candidates" if not matching else
             "session_exhausted" if not available else "caught_up")
    return {"policy": POLICY, "state": state, "recommendations": selected,
            "history": {"scope": "latest_recorded_submissions", "limit": HISTORY_LIMIT,
                        "truncated": len(history) > HISTORY_LIMIT, "mapped_problems": len(seen),
                        "unmapped_submissions": unmapped, "invalid_timestamps": invalid,
                        "dated_exposures": len(dated), "calendar_timezone": "UTC"},
            "limitations": ["Recorded practice does not establish correctness or mastery.",
                            "Shared catalog topics do not prove the same algorithm is required.",
                            "Seven elapsed days is a scheduling heuristic, not predicted forgetting."],
            "summary": {"primary_weak_patterns": [], "focus_area": "", "recommendation_strategy": POLICY}}
