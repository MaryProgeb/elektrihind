# Tasks

## 1. Multi-day price input

- [x] 1.1 Add an Elering local-date range fetch for today through tomorrow while preserving the existing one-day fetch; verify fixture tests for UTC query bounds, filtering both dates, and DST-length ranges.
- [x] 1.2 Validate tomorrow's series has exactly one interval at every expected 15-minute start; verify fixtures cover complete 92-, 96-, and 100-interval days plus missing, partial, and duplicate intervals.

## 2. Afternoon window selection and message

- [x] 2.1 Add afternoon cutoff and exclusive end-bound handling that permits midnight-crossing windows only in the afternoon flow; verify a 15:07 run first permits 15:15, delayed-publication cutoffs advance to the next boundary, and exact-midnight inclusion, over-bound exclusion, and DST elapsed duration.
- [x] 2.2 Add the Estonian afternoon message formatter with date-qualified endpoints and `Perioodi keskmine`; verify format tests for tomorrow-only and midnight-crossing windows, period average, empty results, and VAT footer.

## 3. Afternoon command and bounded polling

- [x] 3.1 Implement the afternoon runner to retry incomplete or failed price fetches every five minutes through a final 18:00 Europe/Tallinn attempt, recompute its slot cutoff when complete data arrives, and never send partial data or poll after the deadline; verify injected-clock tests for first-poll success, later publication, and deadline failure with no Telegram send.
- [x] 3.2 Add `python -m elektrihind afternoon` while retaining the default morning invocation; verify CLI tests route each invocation to its flow and both report errors without live Elering or Telegram calls.

## 4. Deployment and operator documentation

- [x] 4.1 Add a separate afternoon GitHub Actions workflow scheduled for 15:07 Europe/Tallinn with manual dispatch, existing Telegram secrets, and enough job timeout to reach the 18:00 deadline; verify its YAML with `actionlint` and confirm its command, timezone, and secret mappings.
- [x] 4.2 Update README schedule, afternoon command, polling/deadline behavior, and manual retry instructions; verify all documented command and workflow names match the implementation.

## 5. Integration validation

- [x] 5.1 Run `pytest` and `openspec validate add-afternoon-tomorrow-slots --strict`; confirm the full fixture suite passes and all change artifacts validate.
