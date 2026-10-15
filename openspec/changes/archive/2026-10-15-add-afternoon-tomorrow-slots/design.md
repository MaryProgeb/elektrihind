# Design

## Context

See `proposal.md` for the motivation and `specs/` for behavior contracts. The morning path currently fetches one Tallinn civil day, cuts off at 08:00/current time, rejects windows crossing midnight, formats a daily message, and is invoked by one scheduled GitHub Actions workflow. The afternoon path needs a two-day range, a bounded wait for publication, and an independent deployment schedule without changing that morning behavior.

## Goals / Non-Goals

**Goals:**
- Reuse the existing Elering client, slot scoring, VAT formatting, and Telegram delivery where their contracts fit.
- Keep polling bounded and deterministic in tests, including across Europe/Tallinn DST changes.
- Send only when tomorrow's complete 15-minute series is available.

**Non-Goals:**
- Change the 08:00 morning selection or message.
- Add a price database, persistent retry state, recommendation to wash/wait, or a live-service test dependency.
- Fetch prices beyond the full next local calendar day.

## Decisions

### Keep the morning path as the default and add an afternoon CLI mode

Keep `python -m elektrihind` as the morning entry point and add `python -m elektrihind afternoon` for the new path. Put the afternoon schedule in a separate workflow so the existing short morning job remains independent of the afternoon polling window. Both workflows use the existing Telegram secrets and retain manual dispatch.

Alternative: select a path based on wall-clock time in the existing default command. Rejected because a manual run would silently select different behavior depending on when it starts.

### Fetch the afternoon range in one Elering request

Request the UTC instants corresponding to local midnight today through local midnight after tomorrow, parse the EE timestamps in Europe/Tallinn, and retain the two requested local dates. Leave the existing one-day fetch behavior available to the morning path. Consider tomorrow complete only when every expected 15-minute start for that civil date is present (92, 96, or 100 intervals according to DST).

Alternative: issue separate requests per date. Rejected because one range request keeps each poll to one API call and avoids combining responses from different publication states.

### Poll at five-minute intervals with an 18:00 local deadline

The scheduled workflow begins at 15:07 Europe/Tallinn. On an incomplete or failed fetch, retry every five minutes, truncating the last wait if necessary to make one final attempt at 18:00 local time. Stop and send once the complete next-day series is available. If it remains unavailable on the 18:00 attempt, return a non-zero result without posting. A manual dispatch runs the same afternoon mode and availability rules; if data is already complete it sends on its first fetch, provided the deadline has not passed.

Inject the clock and wait function (or equivalent) into the afternoon runner so tests can advance time without real sleeps. Use Europe/Tallinn civil times for the deadline, not a fixed UTC offset.

Alternative: one fetch at 15:07 with manual retry. Rejected because a normal publication delay would miss the automatic message. Unbounded retry is rejected because it could leave the Actions job running overnight.

### Keep slot times as instants and apply explicit period bounds

Build the afternoon eligible series from the later of 15:00 today or the first 15-minute boundary at/after the time a complete series is obtained, through the exclusive local-midnight boundary after tomorrow. Thus a run starting at 15:07 cannot use the 15:00 interval and may first select a window starting at 15:15; delayed publication advances this cutoff. Generate contiguous 12-interval windows using epoch instants so a three-hour window remains three elapsed hours across DST transitions. Permit crossing midnight in the afternoon path only; keep morning windows on one local date. Rank using the existing mean-price and non-overlap rules.

Alternative: extend the morning's `latest_end` time-of-day bound. Rejected because a time-only bound cannot express the next-local-midnight limit across two dates or DST unambiguously.

### Format afternoon dates explicitly

Add an Estonian formatter for the multi-day message. Include `täna`, `homme`, or `ülehomme` with endpoints whose local dates need disambiguation, use `Perioodi keskmine` for the mean of eligible intervals, and keep the existing VAT/no-network-fee footer. The morning formatter remains unchanged.

## Risks / Trade-offs

- [Elering returns an incomplete or delayed series] → Poll only until 18:00; never publish rankings from partial tomorrow data and surface deadline failure in the workflow.
- [A late successful poll leaves fewer usable evening intervals] → Recompute the cutoff when the complete series is obtained and exclude products that have already started.
- [GitHub delays or drops a scheduled run] → Preserve manual dispatch; do not add persistent state or automatic schedule replay.
- [DST makes wall-clock duration misleading] → Use actual interval instants for continuity, window length, and local-day range boundaries.

## Migration Plan

1. Add and verify the afternoon CLI mode, two-day fetch, bounded window selection, message formatter, and fixture-based tests without changing the default command.
2. Add the separate afternoon GitHub Actions workflow with the existing secret names, 15:07 Europe/Tallinn schedule, manual dispatch, and a job timeout long enough to reach the 18:00 application deadline.
3. Update README behavior and manual-retry instructions. Merge the workflow to the default branch to enable its schedule.
4. Roll back by disabling/removing only the afternoon workflow and mode; the morning workflow remains operational.
