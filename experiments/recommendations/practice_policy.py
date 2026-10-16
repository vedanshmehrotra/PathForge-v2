"""Isolated prototype. No runtime API imports or changes to learner state."""

import argparse
import json
from pathlib import Path

from pathforge.recommendation_links import problem_url

CATALOG = Path(__file__).with_name("practice_catalog.json")
POLICY = "guided_practice_prototype_v1"
DIFFICULTIES = {"Easy", "Medium", "Hard"}


def load_catalog(path=CATALOG):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("version"), str) or not raw["version"]:
        raise ValueError("Catalog version is required")
    if not isinstance(raw.get("items"), list):
        raise ValueError("Catalog items must be a list")
    seen_ids, seen_urls = set(), set()
    for item in raw["items"]:
        if not isinstance(item, dict):
            raise ValueError("Catalog item must be an object")
        if type(item.get("leetcode_id")) is not int or item["leetcode_id"] < 1:
            raise ValueError("A LeetCode frontend ID is required")
        if any(not isinstance(item.get(key), str) or not item[key].strip()
               for key in ("title", "topic", "checked_on")):
            raise ValueError("Title, topic and source check date are required")
        url = problem_url(item.get("problem_url"))
        if not url or item.get("difficulty") not in DIFFICULTIES:
            raise ValueError("Source difficulty and a valid problem URL are required")
        if item["leetcode_id"] in seen_ids or url in seen_urls:
            raise ValueError("Catalog identities and destinations must be unique")
        seen_ids.add(item["leetcode_id"])
        seen_urls.add(url)
    return raw


def recommend_practice(catalog, selected_topic=None, selected_difficulty=None, excluded_ids=(), limit=3):
    """Filter explicit preferences; preserve catalog order, never infer weakness.

    Accepts the source-checked catalog returned by load_catalog. Exclusions are
    explicit session choices, not solved/mastered labels. No history argument or
    fallback to another recommendation policy exists.
    """
    if selected_difficulty is not None and selected_difficulty not in DIFFICULTIES:
        raise ValueError("Choose Easy, Medium or Hard")
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("Choose a list size between one and five")
    matching = [item for item in catalog["items"]
                if (selected_topic is None or item["topic"] == selected_topic)
                and (selected_difficulty is None or item["difficulty"] == selected_difficulty)]
    excluded = set(excluded_ids)
    available, seen = [], set()
    for item in matching:
        key = item["leetcode_id"]
        if key in excluded or key in seen:
            continue
        seen.add(key)
        available.append({**item, "reason": (
            f"Matches your selected {item['topic']} topic and {item['difficulty']} difficulty."
            if selected_topic and selected_difficulty else
            f"Matches your selected {item['topic']} topic."
            if selected_topic else
            f"From the starter mix at your selected {item['difficulty']} difficulty."
            if selected_difficulty else
            f"From the starter mix; source difficulty is {item['difficulty']}."
        )})
    state = "available" if available else "session_exhausted" if matching else "no_candidates"
    return {"policy": POLICY, "catalog_version": catalog["version"], "state": state,
            "recommendations": available[:limit], "session_only": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic")
    parser.add_argument("--difficulty", choices=sorted(DIFFICULTIES))
    parser.add_argument("--exclude", type=int, nargs="*", default=[])
    args = parser.parse_args()
    print(json.dumps(recommend_practice(load_catalog(), args.topic, args.difficulty, args.exclude), indent=2))
