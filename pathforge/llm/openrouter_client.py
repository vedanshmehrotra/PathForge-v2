import json
import os
import time
import urllib.error
import urllib.request


API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"
TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 1.0


def call_llm(problem_text: str) -> dict | None:
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        return None

    prompt = _build_prompt(problem_text)

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_body = _post_request(prompt, api_key)
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None

        content = _extract_content(payload)
        if content is None:
            return None

        parsed = _parse_llm_json(content)
        if parsed is not None:
            return parsed

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * (attempt + 1))
            continue

    return None


def _build_prompt(problem_text: str) -> str:
    return (
        "You are a precise algorithm classification assistant. "
        "Given a programming problem description, identify the algorithmic patterns "
        "required to solve it. Return ONLY valid JSON with no markdown, no explanation.\n\n"
        "Output format:\n"
        '{"patterns": ["pattern_1", "pattern_2"], "confidence": {"pattern_1": 0.9}}\n\n'
        "Use exactly one of these canonical pattern names (all lowercase, snake_case):\n"
        "hash_map_lookup, hash_map_frequency, prefix_sum, sliding_window_fixed, "
        "sliding_window_variable, two_pointers_opposite, two_pointers_same, "
        "dfs_recursive, dfs_iterative, bfs_level_order, bfs_shortest_path, "
        "topological_sort, union_find, binary_search_tree, "
        "dp_1d_forward, dp_1d_sequence, dp_2d_grid, dp_2d_string, dp_knapsack, "
        "dp_interval, dp_state_machine, "
        "fast_slow_pointers, linked_list_reversal, monotonic_stack, monotonic_deque, "
        "binary_search_standard, binary_search_rotated, binary_search_answer, "
        "heap_top_k, greedy_local, greedy_interval, "
        "backtracking_permutation, backtracking_subset\n\n"
        "Problem:\n"
        f"{problem_text}"
    )


def _post_request(prompt: str, api_key: str) -> bytes:
    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500,
    }).encode("utf-8")

    req = urllib.request.Request(OPENROUTER_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("HTTP-Referer", "https://pathforge.app")

    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _extract_content(payload: dict) -> str | None:
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _parse_llm_json(content: str) -> dict | None:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]
        else:
            return None

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    if "patterns" not in data or not isinstance(data["patterns"], list):
        return None
    if "confidence" in data and not isinstance(data["confidence"], dict):
        data["confidence"] = {}

    return data
