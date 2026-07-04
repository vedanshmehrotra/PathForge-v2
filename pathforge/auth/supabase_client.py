"""Supabase client initialization for PathForge authentication."""

import os
from supabase import create_client, Client

_SUPABASE_URL: str | None = None
_SUPABASE_ANON_KEY: str | None = None
_CLIENT: Client | None = None


def _load_config() -> tuple[str, str]:
    global _SUPABASE_URL, _SUPABASE_ANON_KEY
    if _SUPABASE_URL is None:
        _SUPABASE_URL = os.environ.get(
            "SUPABASE_URL",
            "https://rrriujagbpfhrqzjcxfa.supabase.co",
        )
    if _SUPABASE_ANON_KEY is None:
        _SUPABASE_ANON_KEY = os.environ.get(
            "SUPABASE_ANON_KEY",
            "",
        )
    if not _SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_ANON_KEY must be set in environment or .env"
        )
    return _SUPABASE_URL, _SUPABASE_ANON_KEY


def get_supabase_client() -> Client:
    global _CLIENT
    if _CLIENT is None:
        url, key = _load_config()
        _CLIENT = create_client(url, key)
    return _CLIENT


def get_supabase_config() -> dict[str, str]:
    url, key = _load_config()
    return {"url": url, "anon_key": key}
