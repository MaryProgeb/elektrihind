# Initial plan: cheapest 3-hour electricity slots

**Superseded:** living plan is `openspec/changes/add-daily-cheapest-slots/`. Tomorrow / 15:00 was dropped — one 08:00 today-only Telegram send. Hosting is GitHub Actions (free), not a VPS.

Captured from the first planning session. This is **input** for OpenSpec, not the living spec. After the first change is proposed, `openspec/changes/...` is the source of truth.

## Goal

Find three cheapest **3-hour** electricity windows (from 15-minute Nord Pool EE prices) and send them to a **Telegram channel** each morning. Also consider tomorrow, because some days are too expensive to run the dishwasher.

Today people check https://elektrihind.ee/borsihind/ before running the dishwasher. Host on a Hetzner-like Linux VPS.

## Decisions already made

| Topic | Choice |
| --- | --- |
| Spec workflow | **OpenSpec** |
| Slot selection | **3 non-overlapping 3-hour windows**, remaining day **after 08:00** for the morning send |
| Tomorrow / skip | **08:00 today + ~15:00 tomorrow** |
| Stack | **Python, no Docker** (venv + systemd timers) |

## What it does

1. **08:00 Europe/Tallinn** — 3 cheapest non-overlapping 3-hour windows from **remaining today** (from 08:00 onward).
2. **15:00 Europe/Tallinn** — 3 cheapest non-overlapping 3h windows for **tomorrow**, plus remaining-today vs tomorrow so dishwashing can be skipped if tomorrow is cheaper.

Data: **Elering Live** `GET https://dashboard.elering.ee/api/nps/price` (same source as elektrihind.ee). 15-min Nord Pool EE prices, no API key. **Do not scrape elektrihind.ee.**

Tomorrow’s prices are published ~13:45–15:00 Estonian time, so 15:00 is the reliable second send. If they are missing, retry a few times, then Telegram “homsed hinnad veel pole”.

## Defaults (change in spec if needed)

- Messages in **Estonian**
- Display **senti/kWh with 24% VAT** (no network fee / excise)
- Windows stay inside one calendar day (`Europe/Tallinn`); no midnight wrap
- No quiet hours (2am is allowed); optional `earliest_start` / `latest_end` in config
- Skip advice at 15:00: if tomorrow’s cheapest 3h average **<** remaining today’s cheapest 3h, recommend waiting

## Slot algorithm

A 3h slot = **12 consecutive 15-min** prices. Average those 12.

Greedy non-overlap:

1. Drop intervals that already started (morning: before 08:00).
2. Score every valid 12-interval window.
3. Take the cheapest, remove any window that overlaps it, repeat until 3 (or until none left).
4. If remaining day is shorter than 3h, say so instead of inventing slots.

## OpenSpec layout (target)

```
openspec/
  config.yaml
  specs/                    # living source of truth after first change is archived
  changes/add-daily-cheapest-slots/
    proposal.md
    design.md
    tasks.md
    specs/
      prices/spec.md
      slots/spec.md
      notify/spec.md
      schedule/spec.md
```

First change is the whole MVP. Later tweaks (quiet hours, extra appliances) are new OpenSpec changes.

## App layout (target)

```
src/elektrihind/
  fetch.py      # Elering client
  slots.py      # window search
  notify.py     # Telegram Bot API
  format.py     # Estonian message
  config.py     # env: token, chat id, VAT, timezone
  cli.py        # today | tomorrow
tests/          # fixtures + slot/VAT/format tests
deploy/         # systemd service + two timers
pyproject.toml
.env.example
```

Entry: `python -m elektrihind today` and `python -m elektrihind tomorrow`.

Telegram: bot posts to **your channel** (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`). Create the bot and add it as channel admin.

### Example 08:00

```
Odavaimad 3h ajad täna (alates 08:00)

1. 11:15–14:15   4.2 s/kWh
2. 15:00–18:00   5.1 s/kWh
3. 21:00–00:00   6.8 s/kWh

Päeva keskmine: 9.1 s/kWh
```

### Example 15:00

Tomorrow’s 3 slots, remaining-today cheapest, and skip line if tomorrow wins.

## Hetzner

- Python 3.12+, venv, `pip install -e .`
- VPS timezone `Europe/Tallinn`
- Two systemd timers: `08:00` and `15:00`, `Persistent=true`
- Secrets in `/etc/elektrihind.env` (not in git)
- No Docker, no public HTTP port

## Implementation order (after OpenSpec propose + review)

1. `openspec init` + first change artifacts (proposal, delta specs, design, tasks)
2. Elering fetch + tests
3. Slot finder + tests
4. Message format + Telegram send
5. CLI + systemd units + README (bot setup, env, timers)
6. Run tests / lint

No live Telegram or Elering calls required to finish coding; tests use fixtures.

## Next OpenSpec step

Do **not** treat this file as the living spec.

1. `openspec init` in the repo root
2. Propose first change `add-daily-cheapest-slots` from this plan
3. Review `proposal.md` / `specs/` / `design.md` / `tasks.md`
4. Only then apply (implement)
5. Sync specs into `openspec/specs/`, archive the change
