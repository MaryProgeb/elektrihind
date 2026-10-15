# slots Specification

## Purpose

Selects up to three cheapest non-overlapping 3-hour dishwasher windows from a remaining-day 15-minute price series.

## Requirements

### Requirement: A slot is twelve consecutive intervals
A candidate window SHALL be exactly 12 consecutive 15-minute intervals (3 hours of market products), and its score SHALL be the arithmetic mean of those 12 source prices. In the morning flow, all interval starts in a window MUST belong to the same local calendar day. In the afternoon flow, a window MAY cross local midnight, but MUST remain wholly inside the afternoon search span.

#### Scenario: Valid window
- **WHEN** a flow has at least 12 consecutive eligible intervals within its search span
- **THEN** each candidate covers exactly 12 intervals and three elapsed hours

#### Scenario: Midnight wrap is forbidden
- **WHEN** a morning window would start on one local date and end on the next
- **THEN** that window is not a candidate

#### Scenario: Afternoon window crosses midnight
- **WHEN** 12 consecutive afternoon intervals start at 23:00 today and end at 02:00 tomorrow
- **THEN** the 23:00–02:00 window is a candidate

### Requirement: Afternoon windows are bounded by the 15:00-to-end-of-tomorrow span
The afternoon search SHALL start at the later of 15:00 today in Europe/Tallinn or the first 15-minute boundary at or after the time a complete price series is obtained. Its exclusive end bound SHALL be local midnight after tomorrow. A candidate MUST start at or after the search cutoff and end at or before that bound; a window ending exactly at the bound is eligible. Interval continuity and three-hour duration SHALL be evaluated using elapsed instants so daylight-saving transitions are handled correctly.

#### Scenario: Scheduled cutoff excludes an interval already in progress
- **WHEN** the run starts at 15:07 today
- **THEN** a window may start at 15:15 but not at 15:00

#### Scenario: Delayed publication advances the cutoff
- **WHEN** a complete series is first obtained at 17:07 today
- **THEN** a window may start at 17:15 but not at 17:00

#### Scenario: Window ends exactly at the period bound
- **WHEN** a candidate starts tomorrow at 21:00 and ends at midnight after tomorrow
- **THEN** the candidate is eligible

#### Scenario: Window extends beyond the period bound
- **WHEN** a candidate starts tomorrow at 21:15 and ends after midnight following tomorrow
- **THEN** the candidate is not eligible

### Requirement: Already-started intervals are excluded
The system SHALL drop any interval whose start is before the remaining-day cutoff. The cutoff is the later of run time (aligned to the containing or next 15-minute start) and any configured `earliest_start`. Intervals at or after the cutoff remain eligible.

#### Scenario: Morning remaining day
- **WHEN** the remaining-day cutoff is 08:00 and an interval starts at 07:45
- **THEN** that interval is not eligible

#### Scenario: Interval at cutoff
- **WHEN** the remaining-day cutoff is 08:00 and an interval starts at 08:00
- **THEN** that interval is eligible

### Requirement: Optional latest end bound
If `latest_end` is configured, a window SHALL be eligible only when its end is at or before that local time on the same calendar day. If it is unset, no extra end bound applies.

#### Scenario: Bound applied
- **WHEN** `latest_end` is 22:00
- **THEN** a window ending at 22:15 is not eligible and a window ending at 22:00 is eligible

### Requirement: Greedy non-overlapping selection of three
The system SHALL rank eligible windows by mean source price ascending, breaking ties by earlier start. It SHALL take the cheapest, remove every window that shares any interval with it, and repeat until 3 windows are chosen or none remain. Selected windows MUST not overlap.

#### Scenario: Three cheap windows
- **WHEN** more than three non-overlapping eligible windows exist
- **THEN** the system returns exactly three, cheapest first, with no shared intervals

#### Scenario: Tie on mean price
- **WHEN** two eligible windows have the same mean
- **THEN** the earlier start is preferred

#### Scenario: Overlap discarded
- **WHEN** the cheapest window is 11:00–14:00
- **THEN** a window 12:00–15:00 is not selected

### Requirement: Short remaining day is not padded
If fewer than 12 consecutive eligible intervals remain, the system SHALL return no windows and MUST NOT invent partial or wrapped slots. If at least one window exists but fewer than three, it SHALL return only the windows that exist.

#### Scenario: Less than three hours left
- **WHEN** the remaining day has 11 or fewer consecutive eligible intervals
- **THEN** the result is an empty window list

#### Scenario: Only two fit
- **WHEN** the remaining day can fit two non-overlapping 3-hour windows but not three
- **THEN** the result contains two windows
