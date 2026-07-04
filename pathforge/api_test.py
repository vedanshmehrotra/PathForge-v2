"""Integration tests for the PathForge API layer.

These tests verify the route handlers and service orchestration without
requiring a running server. They test the FastAPI route logic via TestClient.
"""

import json
import pytest
from fastapi.testclient import TestClient
from pathforge.api.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_analyze_missing_code():
    resp = client.post("/analyze", json={"user_id": "1", "language": "python"})
    assert resp.status_code == 422


def test_analyze_invalid_language():
    resp = client.post("/analyze", json={
        "user_id": "1",
        "code": "x = 1",
        "language": "java",
    })
    assert resp.status_code == 400
    detail = resp.json().get("detail", {})
    assert detail.get("stage") == "VALIDATION"


def test_analyze_valid_python():
    code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
    resp = client.post("/analyze", json={
        "user_id": "1",
        "code": code,
        "language": "python",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "ast" in data
    assert "match_result" in data
    assert "detected_patterns" in data["ast"]
    assert data["ast"]["patterns_detected"] >= 1


def test_analyze_syntax_error():
    resp = client.post("/analyze", json={
        "user_id": "1",
        "code": "def broken(",
        "language": "python",
    })
    assert resp.status_code == 400
    detail = resp.json().get("detail", {})
    assert detail.get("stage") == "AST"


def test_gaps_invalid_user():
    resp = client.post("/gaps", json={"user_id": 99999})
    assert resp.status_code == 400
    detail = resp.json().get("detail", {})
    assert "error" in detail


def test_gaps_request_format():
    resp = client.post("/gaps", json={"user_id": "abc"})
    assert resp.status_code == 422


def test_elo_invalid_user():
    resp = client.post("/elo", json={"user_id": 99999})
    assert resp.status_code == 400


def test_elo_request_format():
    resp = client.post("/elo", json={})
    assert resp.status_code == 422


def test_recommend_invalid_user():
    resp = client.post("/recommend", json={"user_id": 99999})
    assert resp.status_code == 400


def test_recommend_request_format():
    resp = client.post("/recommend", json={})
    assert resp.status_code == 422


def test_all_endpoints_respond():
    endpoints = ["/analyze", "/gaps", "/elo", "/recommend"]
    for ep in endpoints:
        resp = client.post(ep, json={})
        assert resp.status_code == 422


def test_analyze_empty_code():
    resp = client.post("/analyze", json={
        "user_id": "1",
        "code": "x = 1",
        "language": "python",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "ast" in data


def test_gaps_missing_user_id():
    resp = client.post("/gaps", json={})
    assert resp.status_code == 422


def test_elo_missing_user_id():
    resp = client.post("/elo", json={})
    assert resp.status_code == 422


def test_recommend_missing_user_id():
    resp = client.post("/recommend", json={})
    assert resp.status_code == 422
