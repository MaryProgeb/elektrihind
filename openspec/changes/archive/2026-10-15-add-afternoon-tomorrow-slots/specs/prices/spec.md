# Spec Delta

## ADDED Requirements

### Requirement: Afternoon search requires a complete next-day EE series
For the afternoon flow, the system SHALL treat tomorrow's prices as available only when the Elering EE response contains exactly one price for every expected 15-minute interval start in tomorrow's Europe/Tallinn civil date. The expected interval count MUST reflect that date's actual 23-, 24-, or 25-hour duration. An empty, partial, or duplicate next-day series MUST be treated as unavailable, not as a usable partial forecast.

#### Scenario: Complete normal next day
- **WHEN** Elering returns all 96 tomorrow interval starts for a 24-hour Europe/Tallinn date
- **THEN** the afternoon flow may use tomorrow's series

#### Scenario: Complete daylight-saving next day
- **WHEN** Elering returns every interval start for a 23-hour or 25-hour Europe/Tallinn date
- **THEN** the afternoon flow may use that complete series with the corresponding 92 or 100 intervals

#### Scenario: Partial next-day publication
- **WHEN** Elering returns some but not all expected interval starts for tomorrow
- **THEN** the next-day series is unavailable to the afternoon flow

#### Scenario: Duplicate next-day interval
- **WHEN** Elering returns more than one price for an expected next-day interval start
- **THEN** the next-day series is unavailable to the afternoon flow
