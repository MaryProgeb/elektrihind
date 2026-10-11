# Design

## Context

See proposal.md — Why. Greenfield Python app; no existing package, tests, or workflow. Constraints from project context: Python 3.12+, no Docker, GitHub Actions free-tier schedule, Elering Live only, Telegram channel, Europe/Tallinn, tests on fixtures. Tomorrow’s day-ahead prices are unpublished at 08:00, so this change never fetches them.

## Goals / Non-Goals

**Goals:**
- Small importable package with a CLI that one scheduled workflow can run.
- Pure slot math and VAT/format logic, easy to unit-test from JSON fixtures.
- Hosted for free on GitHub Actions: one daily schedule plus a manual dispatch, secrets in the repo settings.

**Non-Goals:**
- Tomorrow’s prices, skip-until-tomorrow advice, a 15:00 send, or retry-until-published behavior.
- Web UI, HTTP API, or scraping elektrihind.ee.
- Quiet hours, multi-appliance profiles, or regions other than EE (optional `earliest_start` / `latest_end` only).
- Docker, public ports, or live network calls in CI.

## Decisions

### Package layout
`src/elektrihind/` with `fetch.py`, `slots.py`, `notify.py`, `format.py`, `config.py`, `cli.py`. Entry: `python -m elektrihind` (no subcommands). Alternative: `today`/`tomorrow` subcommands — rejected; there is only one job.

### HTTP client
Use `urllib` (stdlib) for Elering and Telegram so runtime deps stay empty beyond Python 3.12. Alternative: `httpx`/`requests` — nicer API, extra deploy surface; not needed for two GET/POST calls.

### Elering request window
Request `start`/`end` as UTC instants for local midnight → next midnight in `Europe/Tallinn` (`zoneinfo`) for **today only**. Parse `data.ee` only. Treat `success != true`, missing `ee`, or empty list as unavailable.

### Slot algorithm
Score every eligible 12-interval window by mean EUR/MWh. Greedy: sort by mean ascending, then start ascending; take one; drop overlapping; repeat to 3. Overlap = any shared interval index. Tie-break is required for stable tests.

### Remaining-day cutoff
`cutoff = max(now, 08:00)` aligned so an in-progress 15-minute product is excluded (start < now). Optional config `EARLIEST_START` / `LATEST_END` as `HH:MM` local.

### Display conversion
`senti_kwh = eur_mwh * (1 + vat) / 10`, default `VAT=0.24`. Round half away from zero to 1 decimal for messages. Conversion lives in format/display, not in the greedy score (score uses source EUR/MWh so VAT cannot change ranking).

### Telegram
`POST https://api.telegram.org/bot<token>/sendMessage` with `chat_id` and `text`. Config: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, optional VAT/timezone/bounds. `.env.example` documents names for local runs. Production injects the same names from GitHub Actions secrets (not in git).

### Scheduling
One workflow at `.github/workflows/daily.yml` on the default branch. Triggers: `schedule` cron `7 8 * * *` with `timezone: Europe/Tallinn`, plus `workflow_dispatch`. Job: `ubuntu-latest`, setup Python 3.12, `pip install -e .`, `python -m elektrihind` with token and chat id from secrets. Off-hour 08:07 reduces queue delay versus 08:00. Alternative: VPS systemd timer with `Persistent=true` — rejected; user wants a free host. GitHub does not replay a missed schedule.

### Tests
`pytest` + fixture JSON copied from Elering shape. Cover VAT, greedy overlap/ties, short day, DST day length, morning copy. HTTP clients injected or monkeypatched; no live calls.

## Risks / Trade-offs

- [Elering schema or URL drift] → Pin request/response in fixtures; fail unavailable rather than guess.
- [Greedy is not globally optimal] → Spec requires greedy; good enough for three dishwasher windows and easy to test.
- [Telegram outage after prices succeeded] → Non-zero exit so the workflow run fails; no local spool in MVP.
- [GitHub schedule delay or drop] → Accepted for free hosting. Late runs still exclude started intervals. Retry with `workflow_dispatch`.
- [No skip-until-tomorrow] → Accepted; prices for tomorrow do not exist at 08:00.

## Migration Plan

1. Create venv, `pip install -e ".[dev]"`, copy `.env.example` for local runs.
2. Create Telegram bot, add it as channel admin, set token and chat id as GitHub Actions secrets.
3. Merge the workflow onto the default branch so `schedule` can fire.
4. Smoke: run the workflow once via `workflow_dispatch` (real network), then rely on the daily cron.
5. Rollback: disable the workflow in the Actions tab; no data store to unwind.

## Open Questions

None that block specs, approach, or tasks. Bot creation and GitHub secrets happen at deploy time.
