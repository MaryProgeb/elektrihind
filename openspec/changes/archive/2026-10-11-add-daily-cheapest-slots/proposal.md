# Proposal

## Why

People check elektrihind.ee before running the dishwasher and still miss cheap 3-hour windows. This change delivers the first working product: one daily Telegram post at 08:00 with the three cheapest remaining 3-hour Nord Pool EE slots for today.

## What Changes

- Fetch 15-minute Nord Pool Estonia prices from Elering Live (no scraping of elektrihind.ee).
- Select up to three cheapest non-overlapping 3-hour windows inside today in Europe/Tallinn, from 08:00 onward.
- Send one Estonian Telegram message around 08:00.
- Run as a Python CLI from one GitHub Actions scheduled workflow; secrets stay in GitHub Actions secrets, not git.
- Do not fetch, compare, or mention tomorrow. Day-ahead prices for tomorrow are unpublished at 08:00.

## Capabilities

### New Capabilities

- `prices`: Fetch, interpret, and convert Nord Pool EE 15-minute prices for a given Estonian calendar day.
- `slots`: Find up to three cheapest non-overlapping 3-hour windows in a remaining-day price series.
- `notify`: Format an Estonian Telegram message (VAT-inclusive senti/kWh) and post it to a channel.
- `schedule`: Run the 08:00 remaining-today send.

### Modified Capabilities

- None (greenfield).

## Impact

- New Python package (`python -m elektrihind`), tests, `.env.example`, and one GitHub Actions workflow.
- Outbound HTTPS to Elering Live and Telegram Bot API from the Actions runner.
- No VPS, no public HTTP service, no Docker. Free-tier schedule may delay or drop a run; missed runs are not replayed.
- `docs/plan.md` remains historical input; this change’s artifacts are the source of truth until archive.
