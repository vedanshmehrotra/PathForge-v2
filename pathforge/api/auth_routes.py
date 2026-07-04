"""Authentication routes for the PathForge FastAPI application.

Provides:
- GET /auth/session — verify current token, return user info
- GET /auth/me — return current authenticated user profile

All routes use Supabase JWT verification via the auth middleware.
"""

from fastapi import APIRouter, Depends, HTTPException
from pathforge.auth.auth_middleware import (
    VerifiedUser,
    get_current_user,
)
from pathforge.db.db import get_connection
from pathforge.db.profile_manager import get_user_profile
import config

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/session")
def verify_session(user: VerifiedUser = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user_id": user.user_id,
        "supabase_id": user.supabase_id,
        "email": user.email,
    }


@router.get("/me")
def get_me(user: VerifiedUser = Depends(get_current_user)):
    connection = get_connection(config.DATABASE_PATH)
    try:
        row = connection.execute(
            """
            SELECT id, username, email, display_name, experience_level,
                   confident_areas, onboarding_complete, current_streak,
                   last_submission_date, created_at, updated_at
            FROM users WHERE id = ?
            """,
            (user.user_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "user_id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "display_name": row["display_name"],
            "experience_level": row["experience_level"],
            "confident_areas": row["confident_areas"],
            "onboarding_complete": bool(row["onboarding_complete"]),
            "current_streak": row["current_streak"],
            "last_submission_date": row["last_submission_date"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        connection.close()


@router.get("/profile")
def get_profile(user: VerifiedUser = Depends(get_current_user)):
    connection = get_connection(config.DATABASE_PATH)
    try:
        profiles = get_user_profile(connection, user.user_id)
        overall = (
            round(sum(float(p["elo_rating"]) for p in profiles) / max(len(profiles), 1), 2)
            if profiles else 800.0
        )
        return {
            "profiles": profiles,
            "overall_elo": overall,
        }
    finally:
        connection.close()
