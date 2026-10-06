# Schedule: shown as Active but never runs

**Severity:** High. A pipeline that looks scheduled silently never runs, so no data reaches GCS and nothing tells the user.

## What I did

1. Created a schedule for project `NSW_Budget_Cleaning` using the **Custom** option.
2. First tried hourly at minute 10. The schedule showed "At minute 10" and a next run time ("Next run in 48 mins").
3. At about 8:23 PM (2026-10-06, Sydney time) changed the expression to `*/10 * * * *` (every 10 minutes).
4. At about 8:50 PM changed it to `0,10,20,30,40,50 * * * *` (the same schedule written as an explicit minute list).

## What I expected

- The pipeline runs every 10 minutes, starting at the next 10-minute mark.
- "Next run" shows the upcoming time.
- If the expression were unsupported, the form would reject it or show an error.

## What happened

- With `*/10 * * * *`, the schedule showed **Active** with the toggle on, but **"Next run:" was blank**.
- The **Executions** view for the schedule showed **"No results"** at 8:48 PM, about 25 minutes after the change. The schedule never fired.
- No error, warning or log entry was shown when saving the expression or afterwards.
- With `0,10,20,30,40,50 * * * *`, the schedule again did not run.
- A **second schedule** added at about 8:56 PM, due to run at about 9:10 PM, **also did not run** (checked at 9:13 PM).
  So the problem is not limited to one cron expression: no scheduled run has fired for this project at all,
  while manual runs of the same pipeline complete successfully.

## What the logs said

Nothing. No log entry for a skipped, failed or attempted scheduled run.

## Workaround

_To be filled in: the schedule setting that produced a successful run, and when it ran._

## How to reproduce

1. Open any project with a working pipeline and go to **Schedule → Add Schedule**.
2. Choose **Custom** and enter `*/10 * * * *`. Save.
3. Observe that the schedule shows **Active** while **Next run** is blank.
4. Wait 20+ minutes and open the schedule's **Executions** view: it shows "No results".

## Suggested improvement

Validate custom cron expressions when they are saved. If an expression cannot be scheduled, reject it with a clear message rather than showing the schedule as Active. Always show the computed next run time so users can confirm the schedule is correct.
