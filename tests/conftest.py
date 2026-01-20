import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app import create_app


@pytest.fixture()
def app():
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_KEY", "service-key")
    app = create_app("testing")
    app.config.update(
        JWT_SECRET_KEY="test-secret",
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        AUTH_COOKIE_NAME="access_token",
        AUTH_COOKIE_SECURE=False,
        AUTH_COOKIE_SAMESITE="Lax",
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
