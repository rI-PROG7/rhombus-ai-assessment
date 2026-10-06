"""
Shared Playwright setup for the Rhombus AI UI tests.

The tests reuse a saved, logged-in browser session (auth.json, created by save_auth.py)
so they never type credentials. Settings come from environment variables or .env.
"""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

AUTH_FILE = Path(__file__).parent / "auth.json"
BASE_URL = os.getenv("RHOMBUS_BASE_URL", "https://rhombusai.com")
PROJECT_ID = os.getenv("RHOMBUS_PROJECT_ID", "5284")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    if not AUTH_FILE.exists():
        pytest.skip("auth.json not found: run `python save_auth.py` first (see README)")
    return {**browser_context_args, "storage_state": str(AUTH_FILE), "viewport": {"width": 1600, "height": 1000}}


@pytest.fixture
def project_page(page):
    """Open the assessment project and wait until the pipeline canvas is visible."""
    page.set_default_timeout(30_000)
    page.goto(f"{BASE_URL}/workflow/{PROJECT_ID}")
    from playwright.sync_api import expect
    expect(page.get_by_text("Data Input").first).to_be_visible(timeout=60_000)
    return page
