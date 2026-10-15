# Spec Delta

## ADDED Requirements

### Requirement: Afternoon message identifies its multi-day coverage and selected slots
The afternoon Telegram message SHALL be in Estonian and identify coverage from 15:00 today through the end of tomorrow. It SHALL list available selected windows cheapest-first with local start and end times and date labels wherever an endpoint is tomorrow or later, so a midnight crossing is unambiguous. It SHALL include the mean of the eligible afternoon-span price series as `Perioodi keskmine`. Slot prices and the period average SHALL follow the existing senti/kWh, configured-VAT, one-decimal display rule without network fee or excise.

#### Scenario: Window crosses midnight
- **WHEN** a selected window starts at 23:00 today and ends at 02:00 tomorrow
- **THEN** its line identifies both dates, for example `täna 23:00–homme 02:00`

#### Scenario: Window is entirely tomorrow
- **WHEN** a selected window starts and ends tomorrow
- **THEN** its line identifies it as tomorrow's window, for example `homme 01:00–04:00`

#### Scenario: Final window ends at the period boundary
- **WHEN** a selected window runs from 21:00 tomorrow to midnight after tomorrow
- **THEN** its line labels the end as `ülehomme 00:00`

#### Scenario: Afternoon slots and period average are shown
- **WHEN** one or more afternoon windows are selected
- **THEN** the message lists them cheapest-first and includes `Perioodi keskmine`

#### Scenario: No afternoon window fits
- **WHEN** no eligible three-hour window exists in the afternoon span
- **THEN** the message states that the period is too short and lists no invented slots
