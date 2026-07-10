"""JWT verification middleware for Supabase Auth (FastAPI).

Verifies Supabase access tokens using JWKS and resolves the Supabase
user to an internal PathForge user record.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk, JWTError
from jose.constants import Algorithms
from pathforge.db.db import get_connection
from pathforge.db.profile_manager import iso_now
import config

_JWKS_CACHE: Optional[dict] = None
_JWKS_URL: Optional[str] = None
_SUPABASE_PROJECT_REF: Optional[str] = None

bearer_scheme = HTTPBearer(auto_error=False)


def _get_project_ref() -> str:
    global _SUPABASE_PROJECT_REF
    if _SUPABASE_PROJECT_REF is None:
        url = os.environ.get(
            "SUPABASE_URL",
            "https://rrriujagbpfhrqzjcxfa.supabase.co",
        )
        _SUPABASE_PROJECT_REF = url.replace("https://", "").split(".")[0]
    return _SUPABASE_PROJECT_REF


def _get_jwks_url() -> str:
    global _JWKS_URL
    if _JWKS_URL is None:
        ref = _get_project_ref()
        _JWKS_URL = (
            f"https://{ref}.supabase.co/auth/v1/.well-known/jwks.json"
        )
    return _JWKS_URL


def _fetch_jwks() -> dict:
    global _JWKS_CACHE
    if _JWKS_CACHE is None:
        url = _get_jwks_url()
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        _JWKS_CACHE = resp.json()
    return _JWKS_CACHE


def _get_jwk(kid: str) -> Optional[dict]:
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def verify_supabase_token(token: str) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
    except JWTError as e:
        print(f"[AuthMiddleware] Malformed token header: {e}")
        raise HTTPException(status_code=401, detail=f"Malformed token header: {e}")
    except Exception as e:
        print(f"[AuthMiddleware] Cannot decode token: {e}")
        raise HTTPException(status_code=401, detail=f"Cannot decode token: {e}")

    kid = unverified.get("kid")
    if not kid:
        print("[AuthMiddleware] Missing kid in token header")
        raise HTTPException(status_code=401, detail="Missing kid in token header")

    try:
        jwk_data = _get_jwk(kid)
        if jwk_data is None:
            print(f"[AuthMiddleware] No matching JWK found for kid: {kid}")
            raise HTTPException(status_code=401, detail="No matching JWK found")
        # Pass the algorithm hint so python-jose constructs EC keys (ES256) correctly
        alg = unverified.get("alg", "RS256")
        public_key = jwk.construct(jwk_data, algorithm=alg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AuthMiddleware] JWK retrieval failed: {e}")
        raise HTTPException(status_code=401, detail=f"JWK retrieval failed: {e}")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[Algorithms.RS256, Algorithms.ES256],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except JWTError as e:
        print(f"[AuthMiddleware] Invalid token signature/claims: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    return payload


def _ensure_local_user(payload: dict, db_path: str) -> int:
    supabase_id = payload.get("sub")
    email = payload.get("email", "")
    if not supabase_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    connection = get_connection(db_path)
    try:
        try:
            row = connection.execute(
                "SELECT id, supabase_id FROM users WHERE supabase_id = ?",
                (supabase_id,),
            ).fetchone()
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error during user lookup: {e}")

        if row is not None:
            return int(row["id"])

        display_name = (
            payload.get("user_metadata", {}).get("full_name")
            or payload.get("user_metadata", {}).get("name")
            or email.split("@")[0]
        )

        now = iso_now()
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, display_name,
                    experience_level, confident_areas, onboarding_complete,
                    supabase_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    supabase_id,
                    email or f"user-{supabase_id[:8]}@placeholder.com",
                    "",
                    display_name,
                    "beginner",
                    "[]",
                    0,
                    supabase_id,
                    now,
                    now,
                ),
            )
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error during user insert: {e}")
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


class VerifiedUser:
    def __init__(self, user_id: int, supabase_id: str, email: str):
        self.user_id = user_id
        self.supabase_id = supabase_id
        self.email = email


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> VerifiedUser:
    auth_header = request.headers.get("Authorization", "")
    print(f"[AuthMiddleware] Authorization Header: '{auth_header[:30]}...' (length: {len(auth_header)})")
    if not auth_header.startswith("Bearer "):
        print(f"[AuthMiddleware] Rejected: Header does not start with 'Bearer '")
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    payload = verify_supabase_token(token)
    supabase_id = payload.get("sub", "")
    email = payload.get("email", "")

    try:
        db_path = config.DATABASE_PATH
        user_id = _ensure_local_user(payload, db_path)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AuthMiddleware] User resolution failed: {e}")
        raise HTTPException(status_code=500, detail=f"User resolution failed: {e}")

    return VerifiedUser(
        user_id=user_id,
        supabase_id=supabase_id,
        email=email,
    )
