import os
import sys
from pathlib import Path
sys.path.append("./python_modules")
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app import create_app

def pytest_sessionstart(session):
    print("Starting test session...")
    
def pytest_sessionfinish(session, exitstatus):
    print("Test session completed.")

@pytest.fixture(scope="session")
def app():
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not all([jwt_secret, supabase_url, supabase_service_key]):
        raise RuntimeError("Required environment variables are not set.")
    app = create_app("testing")
    app.config.update(
        JWT_SECRET_KEY="test-secret",
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        AUTH_COOKIE_NAME="access_token",
        AUTH_COOKIE_SECURE=False,
        AUTH_COOKIE_SAMESITE="Lax",
    )
    yield app

@pytest.fixture()
def client(app):
    return app.test_client()

# selenium webdriver fixture for integration tests
@pytest.fixture(scope="session")
def driver(request):
    if(request.param == "chrome"):
        print("Setting up WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        yield driver  # provide driver to tests and waits till test completion
        print("Closing WebDriver...") # after test run the control reaches here
        driver.quit()