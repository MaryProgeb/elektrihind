# elektrihind

Sends Estonian Telegram messages to a channel with the cheapest non-overlapping 3-hour
Nord Pool EE windows:

- At 08:07 Europe/Tallinn, compares the remaining intervals today from 08:00 onward.
- At 15:07 Europe/Tallinn, compares the afternoon from 15:00 today through the end of
  tomorrow, including windows that cross midnight.

Prices come from Elering Live and are shown in senti/kWh with 24% VAT (no network fee,
no excise).

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
python -m elektrihind afternoon
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

The workflows are `.github/workflows/daily.yml` and
`.github/workflows/afternoon.yml`. They run `python -m elektrihind` and
`python -m elektrihind afternoon`, respectively, with these repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Add both under **Settings → Secrets and variables → Actions**. Never commit `.env` or
real values to git.

Scheduled runs only fire from the default branch, so merge the workflow there first.
GitHub may delay or drop a scheduled run. Missed runs are not replayed.

To send a message manually (for example to retry after a failed run), open **Actions** and
run either **daily-cheapest-slots** for the remaining-today message or
**afternoon-cheapest-slots** for the afternoon message. Manual runs use the same behavior
and deadline as their scheduled flow.

## Behavior

- The morning flow requests only today's prices. It starts windows at or after the first
  15-minute boundary at or after the run time, and not before 08:00; intervals that already
  started are excluded.
- The afternoon flow requests today and tomorrow in one Elering query. It waits for exactly
  one price at every expected 15-minute start tomorrow (92, 96, or 100 intervals depending
  on DST), retrying failed or incomplete fetches every five minutes through a final attempt
  at 18:00 Europe/Tallinn. It sends nothing if tomorrow's series is still incomplete then.
- Afternoon windows start no earlier than 15:00 and no earlier than the next 15-minute
  boundary when complete prices arrive. At the scheduled 15:07 run, the earliest possible
  start is 15:15. Windows may cross midnight but must end by midnight after tomorrow.
- A failed Telegram send exits non-zero and is not retried automatically. Missed scheduled
  GitHub Actions runs are not replayed.

Optional settings in `.env` (`VAT`, `TIMEZONE`, `EARLIEST_START`, `LATEST_END`) are described
in `.env.example`.
