from pathforge.llm.openrouter_client import call_llm, _build_prompt, _parse_llm_json, _extract_content


def test_build_prompt():
    prompt = _build_prompt("Two Sum problem: find two numbers that add up to target")
    assert "hash_map_lookup" in prompt
    assert "Two Sum" in prompt


def test_parse_llm_json_valid():
    data = '{"patterns": ["hash_map_lookup", "prefix_sum"], "confidence": {"hash_map_lookup": 0.9}}'
    result = _parse_llm_json(data)
    assert result["patterns"] == ["hash_map_lookup", "prefix_sum"]
    assert result["confidence"]["hash_map_lookup"] == 0.9


def test_parse_llm_json_markdown():
    with_code = '```json\n{"patterns": ["bfs_level_order"]}\n```'
    result = _parse_llm_json(with_code)
    assert result["patterns"] == ["bfs_level_order"]


def test_parse_llm_json_invalid():
    result = _parse_llm_json("not json at all")
    assert result is None


def test_parse_llm_json_missing_patterns():
    result = _parse_llm_json('{"foo": "bar"}')
    assert result is None


def test_extract_content():
    payload = {"choices": [{"message": {"content": "hello"}}]}
    assert _extract_content(payload) == "hello"


def test_extract_content_empty():
    assert _extract_content({}) is None


def test_call_llm_no_key():
    import os
    key = os.environ.pop("OPENROUTER_API_KEY", None)
    result = call_llm("test problem")
    assert result is None
    if key:
        os.environ["OPENROUTER_API_KEY"] = key


def test_call_llm_bad_key():
    import os
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        os.environ["OPENROUTER_API_KEY"] = "sk-or-v-bad-key"
    result = call_llm("test problem")
    assert result is None or isinstance(result, dict)
    if not key:
        del os.environ["OPENROUTER_API_KEY"]
