"""Supabase Python client (anon key). Never expose service_role to Flutter."""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY are required for Auth verification."
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)
