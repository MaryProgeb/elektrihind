# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
