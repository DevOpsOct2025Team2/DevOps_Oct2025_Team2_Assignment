import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

from app import create_app


def pytest_sessionstart(session):
    print("Starting test session...")


def pytest_sessionfinish(session, exitstatus):
    print("Test session completed.")


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    app.config.update(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY") or "test-secret",
        SUPABASE_URL=os.getenv("SUPABASE_URL") or "http://localhost",
        SUPABASE_SERVICE_KEY=os.getenv("SUPABASE_SERVICE_KEY") or "test-service-key",
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        AUTH_COOKIE_NAME="access_token",
        AUTH_COOKIE_SECURE=False,
        AUTH_COOKIE_SAMESITE="Lax",
        SECRET_KEY="test-secret",
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


# selenium webdriver fixture for integration tests
@pytest.fixture(scope="session")
def driver(request):
    browser = getattr(request, "param", "chrome")
    if browser == "chrome":
        print("Setting up WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        yield driver
        print("Closing WebDriver...")
        driver.quit()
        return

    raise ValueError(f"Unsupported browser parameter: {browser}")
