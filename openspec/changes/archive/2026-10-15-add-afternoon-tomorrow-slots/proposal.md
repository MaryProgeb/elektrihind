# Proposal

## Why

The 08:00 notification cannot show tomorrow's prices, so a user deciding whether to run a dishwasher later in the day cannot compare tonight's and tomorrow's cheaper periods. Add an afternoon notification after day-ahead prices are published, with a bounded retry period for publication delays.

## What Changes

- Add an afternoon command and scheduled run at 15:07 Europe/Tallinn, polling Elering until tomorrow's complete price series is available or 18:00. Do not send partial results; report unavailable prices if the deadline passes.
- Evaluate 3-hour windows from 15:00 today through the end of tomorrow, allowing a window to cross midnight while keeping it within that span. Exclude intervals that have already started: at the scheduled 15:07 run, the earliest window may start at 15:15; if publication arrives later, advance the cutoff to the next 15-minute boundary.
- Send a separate Estonian message with the three cheapest non-overlapping windows, clear date labels for tomorrow and midnight-crossing times, and the average for the evaluated period.
- Keep the existing 08:00 remaining-today command, message, and schedule unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `schedule`: Add the afternoon scheduled/manual flow and bounded polling alongside the existing morning flow.
- `prices`: Support retrieving and validating the two local calendar days needed for the afternoon span.
- `slots`: Permit midnight-crossing windows only for the afternoon span and bound candidates to that span.
- `notify`: Define the afternoon message, date disambiguation, and period average while preserving morning copy.

## Impact

- Affected code: `src/elektrihind/fetch.py`, `slots.py`, `format.py`, `cli.py`, and package entry-point behavior.
- Affected deployment/docs: add a second GitHub Actions workflow and document its command and polling behavior.
- Affected tests: fixture-based fetch, slot-boundary, formatting, CLI/polling, and schedule checks. No new runtime dependency or live-service test is required.
