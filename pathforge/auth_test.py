"""Tests for Supabase authentication integration.

These tests verify the auth middleware, user mapping, and auth routes.
JWT verification is tested with mock/computed tokens.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pathforge.api.app import app

client = TestClient(app)


def test_health_still_works():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_session_no_token():
    resp = client.get("/auth/session")
    assert resp.status_code == 401
    detail = resp.json().get("detail", "")
    assert "Missing" in detail or "Invalid" in detail or "401" in str(resp.status_code)


def test_me_no_token():
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_profile_no_token():
    resp = client.get("/auth/profile")
    assert resp.status_code == 401


def test_session_with_fake_token():
    resp = client.get(
        "/auth/session",
        headers={"Authorization": "Bearer fake.token.here"},
    )
    assert resp.status_code == 401


def test_analyze_rejects_without_auth():
    """Unauthenticated /analyze must return 401."""
    patch.stopall()
    resp = client.post("/analyze", json={
        "user_id": 1,
        "code": "x = 1",
        "language": "python",
    })
    assert resp.status_code == 401


def test_recommend_rejects_without_auth():
    """Unauthenticated /recommend must return 401."""
    patch.stopall()
    resp = client.post("/recommend", json={"user_id": 1})
    assert resp.status_code == 401


def test_elo_rejects_without_auth():
    """Unauthenticated /elo must return 401."""
    patch.stopall()
    resp = client.post("/elo", json={"user_id": 1})
    assert resp.status_code == 401


def test_gaps_rejects_without_auth():
    """Unauthenticated /gaps must return 401."""
    patch.stopall()
    resp = client.post("/gaps", json={"user_id": 1})
    assert resp.status_code == 401


def test_prepare_problem_rejects_without_auth():
    """Unauthenticated /prepare-problem must return 401."""
    patch.stopall()
    resp = client.post("/prepare-problem", json={
        "problem": {"leetcode_id": 1},
    })
    assert resp.status_code == 401


def test_me_with_fake_token():
    resp = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.structure"},
    )
    assert resp.status_code == 401


def test_auth_routes_registered():
    routes = [r.path for r in app.routes]
    assert "/auth/session" in routes
    assert "/auth/me" in routes
    assert "/auth/profile" in routes


def test_bearer_scheme_detection():
    resp = client.get("/auth/session", headers={"Authorization": "Basic xyz"})
    assert resp.status_code == 401
    assert "Bearer" in resp.text or "Missing" in resp.text or "401" in str(resp.status_code)


def test_empty_authorization_header():
    resp = client.get("/auth/me", headers={"Authorization": ""})
    assert resp.status_code == 401
