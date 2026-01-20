import os
from supabase import create_client

_supabase_client = None


def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not service_key:
        raise RuntimeError("Supabase credentials are missing.")

    _supabase_client = create_client(url, service_key)
    return _supabase_client
