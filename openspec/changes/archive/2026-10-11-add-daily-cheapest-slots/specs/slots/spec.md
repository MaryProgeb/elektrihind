# Spec Delta

## Purpose

Selects up to three cheapest non-overlapping 3-hour dishwasher windows from a remaining-day 15-minute price series.

## ADDED Requirements

### Requirement: A slot is twelve consecutive intervals
A candidate window SHALL be exactly 12 consecutive 15-minute intervals (3 hours of market products). Its score SHALL be the arithmetic mean of those 12 source prices. Windows MUST NOT wrap past local midnight.

#### Scenario: Valid window
- **WHEN** a day has at least 12 consecutive remaining intervals
- **THEN** each candidate covers 12 intervals and stays on that calendar day

#### Scenario: Midnight wrap is forbidden
- **WHEN** a window would start on one local date and end on the next
- **THEN** that window is not a candidate

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
