import json
import os
import time
import urllib.error
import urllib.request

from pathforge.analysis_capabilities import prompt_pattern_vocabulary


API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 1000
TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 1.0


def call_llm(problem_text: str) -> dict | None:
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        return None

    model = os.getenv("OPENROUTER_MODEL", MODEL).strip()
    try:
        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", str(MAX_TOKENS)))
    except ValueError:
        return None
    if not model or max_tokens <= 0:
        return None

    prompt = _build_prompt(problem_text)

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_body = _post_request(prompt, api_key, model=model, max_tokens=max_tokens)
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
        "Given a programming problem description, propose distinct solution approaches. "
        "An approach may combine several required patterns; different technique categories "
        "do not make them alternative solutions. List alternatives explicitly. "
        "Do not force an unsupported approach into the vocabulary or claim exhaustive coverage. "
        "Return ONLY valid JSON with no markdown, no explanation.\n\n"
        "Output format:\n"
        '{"approach_contract_version": 2, "patterns": ["pattern_1", "pattern_2"], "confidence": {"pattern_1": 0.9}, '
        '"approaches": [{"name": "One combined approach", "patterns": ["pattern_1", "pattern_2"], '
        '"confidence": {"pattern_1": 0.9, "pattern_2": 0.8}}]}\n\n'
        "The top-level patterns must be the union of all approach patterns. "
        "Include one or more approaches; retain all required components within each. "
        "For an approach that cannot be COMPLETELY represented by these pattern names, retain it as "
        '{"name": "Approach name", "description": "How this approach works", "patterns": [], '
        '"comparison_support": "UNSUPPORTED", "coverage_limit": "Which essential components cannot be represented"}. '
        "Keep these descriptive alternatives alongside supported approaches. Do not drop unsupported components "
        "to make a partly representable approach appear complete. If all approaches are descriptive, top-level "
        "patterns and confidence are empty but approaches is nonempty. Empty or malformed output is a failure. "
        "These are unverified proposals, not correctness, optimality or skill judgments. Exhaustive enumeration "
        "can be appropriate when all combinations are the required output. Ordinary bracket stacks are not "
        "monotonic stacks, and nesting-depth counters are not fixed windows. Prefix products are not additive "
        "prefix sums; preserve them as descriptive approaches when no complete supported definition fits. Do not force missing vocabulary "
        "into a nearby pattern. Use only the component IDs and definitions below. "
        "Observations such as sorting and array_traversal may be combined in an explicitly named "
        "approach, but do not establish a confirmed strategy, correctness, optimality or a rated skill. "
        "Describe a genuinely different unsupported mechanism as an unsupported alternative, "
        "even when a supported alternative also exists. Do not present the list as exhaustive.\n"
        f"{prompt_pattern_vocabulary()}\n\n"
        "Problem:\n"
        f"{problem_text}"
    )


def _post_request(prompt: str, api_key: str, *, model: str = MODEL, max_tokens: int = MAX_TOKENS) -> bytes:
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(OPENROUTER_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("HTTP-Referer", "https://pathforge.app")

    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _extract_content(payload: dict) -> str | None:
    try:
        choice = payload["choices"][0]
        if not isinstance(choice, dict):
            return None
        # An explicitly truncated/failed result is not a complete expectation,
        # even if the partial content happens to parse as valid JSON.
        # Missing finish metadata remains compatible with older fixtures.
        if choice.get("finish_reason") not in (None, "stop"):
            return None
        content = choice["message"]["content"]
        return content if isinstance(content, str) and content.strip() else None
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
