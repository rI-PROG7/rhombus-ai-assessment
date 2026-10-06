# UI tests (Playwright, Python)

Browser tests for the Rhombus AI pipeline journey in project `NSW_Budget_Cleaning`:
S3 connection, AI-built pipeline, GCS destination and schedule.

## Status

**Written but not yet executed end to end.** Playwright needs a logged-in session (`auth.json`), and the
Rhombus login (Google sign-in) refused to complete inside the Playwright-controlled browser. `save_auth.py`
includes a workaround that copies the session from a normal Chrome window started with remote debugging,
but there was no time left in the assessment to finish it. Selectors are based on the labels visible in the
Rhombus UI and may need adjusting on the first run.

This is itself a finding: the sign-in flow blocks the kind of automated UI testing a customer's QA team would run.

## Tests

| Test | What it checks | Default |
|---|---|---|
| `test_project_canvas_shows_input_and_output` | Project opens; canvas shows Data Input and Data Output | runs |
| `test_s3_connection` | Fills the Amazon S3 form and expects a successful connection, not the access-denied error | runs, **expected to fail** (known S3 issue) |
| `test_ai_built_pipeline_nodes_present` | The six AI-built cleaning nodes are on the canvas | runs |
| `test_ai_builder_responds_to_prompt` | Sends a read-only prompt to the AI builder and waits for a reply naming the nodes | opt-in: `RUN_AI_BUILDER=1` |
| `test_gcs_destination_selected` | Data Output has the GCS destination selected with CSV format | runs |
| `test_schedule_is_active` | The schedule exists and is Active | runs |
| `test_schedule_shows_next_run_time` | "Next run" shows a time | runs, **expected to fail** (known schedule issue) |
| `test_manual_run_completes` | Runs the pipeline and waits for "Pipeline completed successfully" in Logs | opt-in: `RUN_PIPELINE=1` |

Design choices:

- **No fixed sleeps.** Every wait is `expect(...)` with a timeout, so tests move on as soon as the UI is ready.
- **Real outcomes.** Assertions check what the UI shows (nodes, selected destination, schedule status, log
  messages), not just that a click happened.
- **Read-only by default.** Tests that spend AI credits, edit the pipeline or write to GCS are opt-in.
- **Known bugs as expected failures.** The S3 and schedule tests are marked `xfail` with a link to the
  observation, so the suite documents them instead of hiding them.

## Setup

From the repo root:

```bash
source .venv/bin/activate
pip install -r ui-tests/requirements.txt
playwright install chromium
```

Save a logged-in session (see the steps at the top of `save_auth.py`):

1. Quit Chrome, then start it with remote debugging:
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/.rhombus-chrome"
   ```
2. Log in to rhombusai.com in that window and open the project.
3. In another terminal: `cd ui-tests && python save_auth.py`

`auth.json` is in `.gitignore` and must never be committed.

## Run

```bash
cd ui-tests
python -m pytest -v                                # read-only suite
RUN_PIPELINE=1 python -m pytest -v                 # also run the pipeline
python -m pytest -v --tracing=retain-on-failure    # keep a Playwright trace for failures
```

Optional settings (environment variables or `.env`): `RHOMBUS_PROJECT_ID` (default `5284`),
`RHOMBUS_GCS_DESTINATION`, `RHOMBUS_S3_BUCKET`, `RHOMBUS_S3_REGION`, `RHOMBUS_SCHEDULE_NAME`.
