"""
Save a logged-in Rhombus AI browser session to auth.json for the UI tests.

Google sign-in usually refuses to log in inside a browser that Playwright launched
("This browser or app may not be secure"). So this script uses your normal Google
Chrome instead: you start Chrome with remote debugging, log in there like a normal
user, and this script copies the session from that Chrome into auth.json.

Steps (macOS):
  1. Quit Chrome completely (Cmd+Q).
  2. In Terminal, start a separate Chrome profile with debugging on:
       "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         --remote-debugging-port=9222 --user-data-dir="$HOME/.rhombus-chrome"
  3. In that Chrome window, go to https://rhombusai.com, log in, and open your project.
  4. In a second Terminal tab (ui-tests/, venv active):
       python save_auth.py
  5. auth.json is written. It is in .gitignore: never commit it.

Fallback: `python save_auth.py --launch` opens a Playwright-controlled Chrome instead
(works for email/password logins, often blocked for Google sign-in).
"""
import sys

from playwright.sync_api import sync_playwright

AUTH_FILE = "auth.json"
CDP_URL = "http://localhost:9222"

with sync_playwright() as p:
    if "--launch" in sys.argv:
        browser = p.chromium.launch(headless=False, channel="chrome",
                                    args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://rhombusai.com/")
        input("Log in in the browser window, open your project, then press Enter here... ")
        context.storage_state(path=AUTH_FILE)
        browser.close()
    else:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            sys.exit(f"Could not reach Chrome at {CDP_URL}. Start Chrome with "
                     f"--remote-debugging-port=9222 first (see the steps at the top of this file).\n{exc}")
        context = browser.contexts[0]
        context.storage_state(path=AUTH_FILE)
    print(f"Saved session to {AUTH_FILE}")
