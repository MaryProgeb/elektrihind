# Tasks

## 1. Package skeleton

- [x] 1.1 Add `pyproject.toml` (Python ≥3.12, pytest extra, package `elektrihind` under `src/`) and verify `pip install -e ".[dev]"` succeeds
- [x] 1.2 Add `src/elektrihind/__init__.py`, `__main__.py`, empty modules from design (`fetch`, `slots`, `notify`, `format`, `config`, `cli`) and verify `python -m elektrihind` imports
- [x] 1.3 Add `.env.example` with `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `VAT`, `TIMEZONE`, optional `EARLIEST_START`/`LATEST_END` and verify names match `config.py` once it exists

## 2. Config

- [x] 2.1 Implement env loading (token, chat id, VAT default 0.24, timezone `Europe/Tallinn`, optional time bounds) and verify unit tests cover defaults and missing required secrets

## 3. Prices

- [x] 3.1 Add Elering JSON fixtures (normal 24h EE day, empty `ee`, unsuccessful payload, DST 23h or 25h) under `tests/fixtures/` and verify files parse as Elering-shaped JSON
- [x] 3.2 Implement EE fetch for today’s `Europe/Tallinn` calendar day via stdlib HTTP and verify tests pass for success, empty, and transport-failure → unavailable (HTTP mocked)
- [x] 3.3 Implement EUR/MWh → senti/kWh VAT conversion and verify tests for 100 EUR/MWh → 12.4 and a negative price

## 4. Slots

- [x] 4.1 Implement 12-interval window scoring and remaining-day cutoff (exclude started intervals, optional `earliest_start`/`latest_end`, no midnight wrap) and verify tests for 08:00 cutoff, interval at cutoff, and `latest_end`
- [x] 4.2 Implement greedy three-window selection (mean then earlier start, drop overlaps) and verify tests for three results, tie-break, overlap discard, short day → empty, and only-two-fit

## 5. Notify

- [x] 5.1 Implement Estonian daily message format (1 decimal s/kWh, `Päeva keskmine`, short-day copy, no tomorrow/skip text) and verify format tests against spec examples
- [x] 5.2 Implement Telegram `sendMessage` and missing-secret behavior and verify tests with a fake HTTP client (no live Telegram)

## 6. CLI

- [x] 6.1 Implement `python -m elektrihind` wiring fetch → slots → notify for remaining today and verify CLI tests drive fixtures/fakes through that flow

## 7. Deploy artifacts

- [x] 7.1 Add `.github/workflows/daily.yml` (`schedule` cron `7 8 * * *` with `timezone: Europe/Tallinn`, `workflow_dispatch`, Python 3.12, `python -m elektrihind`, secrets as env) and verify the YAML invokes that command
- [x] 7.2 Add README (venv, `.env.example` for local, bot as channel admin, GitHub secrets, default-branch schedule, manual dispatch, no Docker, missed runs not replayed) and verify it documents the same command and secret names as the workflow

## 8. Integration check

- [x] 8.1 Run the full pytest suite with no live network and verify all tests pass
