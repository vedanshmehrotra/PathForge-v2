import time

import requests

from pathforge.config import (
    JUDGE0_API_HOST,
    JUDGE0_API_KEY,
    JUDGE0_BASE_URL,
    JUDGE0_TIMEOUT_SECONDS,
)

ACCEPTED_STATUS_ID = 3
TLE_STATUS_ID = 5
COMPILATION_ERROR_STATUS_ID = 6
RUNTIME_ERROR_STATUS_ID = 11


def run_single_test(source_code, language_id, stdin):
    """Run one test case through Judge0 and return the raw response dictionary."""
    if not JUDGE0_API_KEY:
        return {"error": "Judge0 API key is not configured"}

    url = f"{JUDGE0_BASE_URL.rstrip('/')}/submissions"
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": JUDGE0_API_KEY,
        "X-RapidAPI-Host": JUDGE0_API_HOST,
    }
    params = {"base64_encoded": "false", "wait": "true"}
    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
    }

    for attempt in range(2):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                params=params,
                timeout=JUDGE0_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return response.json()
            if attempt == 0:
                time.sleep(1)
        except requests.RequestException as exc:
            if attempt == 0:
                time.sleep(1)
                continue
            return {"error": f"Judge0 unavailable: {exc}"}

    return {
        "error": "Judge0 returned a non-200 response",
        "http_status": response.status_code,
        "body": response.text,
    }


def evaluate_submission(source_code, language_id, test_cases):
    """Run all test cases and return PathForge's structured evaluation result."""
    results = []
    first_failure = None

    for index, test_case in enumerate(test_cases, start=1):
        expected = str(test_case.get("expected", "")).strip()
        stdin = test_case.get("input", "")
        raw = run_single_test(source_code, language_id, stdin)
        result = _build_test_result(index, raw, expected)
        results.append(result)

        if not result["passed"] and first_failure is None:
            first_failure = {
                "test_case": index,
                "reason": result["failure_reason"],
                "status": result["status"],
                "actual_output": result["actual_output"],
                "expected_output": expected,
            }

    has_error = any(result["status_id"] in (COMPILATION_ERROR_STATUS_ID, RUNTIME_ERROR_STATUS_ID) or result["status"] == "Error" for result in results)
    has_tle = any(result["status_id"] == TLE_STATUS_ID for result in results)
    all_passed = bool(results) and all(result["passed"] for result in results)

    if all_passed:
        verdict = "pass"
    elif has_tle:
        verdict = "tle"
    elif has_error:
        verdict = "error"
    else:
        verdict = "fail"

    return {
        "verdict": verdict,
        "passed": verdict == "pass",
        "test_results": results,
        "first_failure": first_failure,
    }


def get_verdict(evaluation_result):
    """Return pass, fail, error, or tle from a structured evaluation result."""
    return evaluation_result.get("verdict", "error")


def _build_test_result(index, raw_response, expected):
    """Normalize one Judge0 response into a per-test result dictionary."""
    if raw_response.get("error"):
        return {
            "test_case": index,
            "status_id": None,
            "status": "Error",
            "actual_output": "",
            "expected_output": expected,
            "execution_time": None,
            "memory": None,
            "stderr": raw_response.get("error"),
            "passed": False,
            "failure_reason": raw_response.get("error"),
            "raw_response": raw_response,
        }

    status = raw_response.get("status") or {}
    status_id = status.get("id")
    status_description = status.get("description", "Unknown")
    actual = (raw_response.get("stdout") or "").strip()
    passed = status_id == ACCEPTED_STATUS_ID and actual == expected

    if passed:
        failure_reason = None
    elif status_id != ACCEPTED_STATUS_ID:
        failure_reason = status_description
    else:
        failure_reason = "Wrong output"

    return {
        "test_case": index,
        "status_id": status_id,
        "status": status_description,
        "actual_output": actual,
        "expected_output": expected,
        "execution_time": raw_response.get("time"),
        "memory": raw_response.get("memory"),
        "stderr": raw_response.get("stderr"),
        "passed": passed,
        "failure_reason": failure_reason,
        "raw_response": raw_response,
    }
