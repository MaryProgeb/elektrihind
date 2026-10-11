# elektrihind

Once a day at 08:07 (Europe/Tallinn), sends one Estonian Telegram message to a channel
with the three cheapest non-overlapping 3-hour Nord Pool EE windows left today, from 08:00
onward. Prices come from Elering Live. Prices are shown in senti/kWh with 24% VAT
(no network fee, no excise).

Runs as a Python CLI on a GitHub Actions schedule. No Docker, no server, no public port.

## Local setup

Requires Python 3.12+.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Create a local `.env` from the example and fill in the Telegram values:

```sh
cp .env.example .env
```

The program reads environment variables only (it does not load `.env` itself), so export
them before running:

```sh
set -a; . ./.env; set +a
python -m elektrihind
```

Run the tests (no network calls are made):

```sh
pytest
```

## Telegram setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Create a channel and add the bot as an administrator with permission to post.
3. Get the channel's chat id (for example `-100...`) and use it as `TELEGRAM_CHAT_ID`.

## GitHub Actions setup

The workflow is `.github/workflows/daily.yml`. It runs `python -m elektrihind` with these
repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Add both under **Settings → Secrets and variables → Actions**. Never commit `.env` or
real values to git.

Scheduled runs only fire from the default branch, so merge the workflow there first.
GitHub may delay or drop a scheduled run. Missed runs are not replayed.

To send the message manually (for example to retry after a failed run), open
**Actions → daily-cheapest-slots → Run workflow**. Manual runs do the same remaining-today
send as the scheduled run.

## Behavior

- Only today's prices (Europe/Tallinn calendar day) are requested. Tomorrow is never fetched.
- Windows start at or after the first 15-minute boundary at or after the run time, and not
  before 08:00. Intervals that already started are excluded.
- If prices are unavailable or the Telegram send fails, the run exits non-zero and nothing
  is retried.

Optional settings in `.env` (`VAT`, `TIMEZONE`, `EARLIEST_START`, `LATEST_END`) are described
in `.env.example`.
