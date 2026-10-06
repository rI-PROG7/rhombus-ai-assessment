"""
UI tests for the Rhombus AI pipeline journey: S3 connection, AI-built pipeline,
GCS destination and schedule.

- No fixed sleeps: every wait is a Playwright `expect(...)` with a timeout.
- Assertions check what the UI actually shows (nodes, selected destination,
  schedule state, run status), not just that a click happened.
- Tests that change the project or spend AI credits are opt-in via environment
  variables, so a normal run is read-only.

Run:  python -m pytest -v
"""
import os
import re

import pytest
from playwright.sync_api import Page, expect

S3_BUCKET = os.getenv("RHOMBUS_S3_BUCKET", "rish-source-bucket")
S3_REGION = os.getenv("RHOMBUS_S3_REGION", "ap-southeast-2")
GCS_DESTINATION = os.getenv("RHOMBUS_GCS_DESTINATION", "rhombus-output-bucket")
SCHEDULE_NAME = os.getenv("RHOMBUS_SCHEDULE_NAME", "Schedule for NSW_Budget_Cleaning")
CLEANING_NODE_LABELS = ["Normalise missing", "Standardise", "Remove exact", "Fill missing", "Convert amount", "Add a new column"]


def open_node(page: Page, label: str):
    page.get_by_text(label, exact=True).first.click()


def test_project_canvas_shows_input_and_output(project_page: Page):
    expect(project_page.get_by_text("Data Input").first).to_be_visible()
    expect(project_page.get_by_text("Data Output").first).to_be_visible()


@pytest.mark.xfail(reason="Known issue: S3 connection rejected despite a matching bucket policy; "
                          "see observations/s3-connection.md", strict=False)
def test_s3_connection(project_page: Page):
    open_node(project_page, "Data Input")
    project_page.get_by_text("Third Party Sources").click()
    project_page.get_by_text("Amazon S3").first.click()
    project_page.get_by_label("Bucket", exact=False).fill(S3_BUCKET)
    project_page.get_by_label("Region", exact=False).fill(S3_REGION)
    project_page.get_by_role("button", name="Connect").click()
    # Real outcome: either a success state or the access-denied error we documented.
    expect(project_page.get_by_text("AWS denied Rhombus AI access")).not_to_be_visible(timeout=60_000)
    expect(project_page.get_by_text(S3_BUCKET).first).to_be_visible()


def test_ai_built_pipeline_nodes_present(project_page: Page):
    for label in CLEANING_NODE_LABELS:
        expect(project_page.get_by_text(label, exact=False).first).to_be_visible()
    # Six AI-built cleaning nodes appear as "Custom" nodes on the canvas.
    expect(project_page.get_by_text("Custom", exact=True)).to_have_count(len(CLEANING_NODE_LABELS))


@pytest.mark.skipif(os.getenv("RUN_AI_BUILDER") != "1",
                    reason="Opt-in: sends a prompt to the AI builder (spends credits, edits the pipeline). Set RUN_AI_BUILDER=1")
def test_ai_builder_responds_to_prompt(project_page: Page):
    project_page.get_by_text("AI Builder").click()
    box = project_page.get_by_role("textbox").last
    box.fill("List the transformation nodes currently on the canvas, in order. Do not change anything.")
    box.press("Enter")
    expect(project_page.get_by_text("data_quality_flag", exact=False).last).to_be_visible(timeout=180_000)


def test_gcs_destination_selected(project_page: Page):
    open_node(project_page, "Data Output")
    project_page.get_by_text("Transform", exact=True).click()
    expect(project_page.get_by_text("Select Destination")).to_be_visible()
    destination = project_page.get_by_text(GCS_DESTINATION).first
    expect(destination).to_be_visible()
    expect(project_page.get_by_role("radio", checked=True).first).to_be_visible()
    expect(project_page.get_by_text("CSV").first).to_be_visible()


def test_schedule_is_active(project_page: Page):
    project_page.get_by_text("Schedule", exact=True).click()
    card = project_page.get_by_text(SCHEDULE_NAME).first
    expect(card).to_be_visible()
    expect(project_page.get_by_text("Active", exact=True).first).to_be_visible()


@pytest.mark.xfail(reason="Known issue: active schedules show a blank 'Next run' and never fire; "
                          "see observations/schedule-custom-cron-not-firing.md", strict=False)
def test_schedule_shows_next_run_time(project_page: Page):
    project_page.get_by_text("Schedule", exact=True).click()
    next_run = project_page.get_by_text("Next run:", exact=False).first
    expect(next_run).to_be_visible()
    # A real next-run time contains a digit (e.g. "in 6 mins" or a timestamp).
    expect(next_run).to_have_text(re.compile(r"Next run:\s*\S*\d"))


@pytest.mark.skipif(os.getenv("RUN_PIPELINE") != "1",
                    reason="Opt-in: runs the pipeline and writes a file to GCS. Set RUN_PIPELINE=1")
def test_manual_run_completes(project_page: Page):
    project_page.get_by_role("button").filter(has=project_page.locator("svg")).nth(1).click()  # play button next to "+"
    project_page.get_by_text("Logs").click()
    expect(project_page.get_by_text("Pipeline completed successfully").first).to_be_visible(timeout=300_000)
    expect(project_page.get_by_text("Pipeline failed")).to_have_count(0)
