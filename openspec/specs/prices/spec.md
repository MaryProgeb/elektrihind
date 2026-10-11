# prices Specification

## Purpose

Fetches Nord Pool Estonia 15-minute day-ahead prices from Elering Live and converts them for slot search and display.

## Requirements

### Requirement: Elering Live is the price source
The system SHALL load Estonia (`ee`) 15-minute Nord Pool prices from Elering Live `GET https://dashboard.elering.ee/api/nps/price`. It MUST NOT scrape elektrihind.ee or any other HTML page.

#### Scenario: Successful EE series
- **WHEN** Elering Live returns a successful payload with a non-empty `data.ee` array
- **THEN** the system uses those `timestamp` and `price` pairs as the Estonia series

#### Scenario: HTML sites are not used
- **WHEN** prices are requested for any calendar day
- **THEN** the system does not request elektrihind.ee or parse HTML for prices

### Requirement: Prices are 15-minute EUR per MWh
Each interval SHALL represent a 15-minute Nord Pool product. The source `price` SHALL be treated as euro per megawatt-hour excluding VAT, network fee, and excise.

#### Scenario: Interval length
- **WHEN** two consecutive EE timestamps are present
- **THEN** they are 15 minutes apart (900 seconds)

### Requirement: Calendar day is Europe/Tallinn
A requested day SHALL be the civil calendar day in `Europe/Tallinn`, including 23-hour and 25-hour DST days. Intervals belong to the day that contains their start instant in that timezone.

#### Scenario: Normal day
- **WHEN** prices are requested for a 24-hour Estonian day
- **THEN** the series covers that day from local midnight up to but not including next midnight

#### Scenario: DST day
- **WHEN** prices are requested for a 23-hour or 25-hour Estonian day
- **THEN** the series includes every published 15-minute interval whose start falls on that local date

### Requirement: Display unit is senti per kWh with VAT
For display, the system SHALL convert source euro/MWh to senti/kWh with the configured VAT rate (default 24%) and MUST NOT add network fee or excise. Conversion MUST be `(EUR/MWh) × (1 + VAT) / 10`.

#### Scenario: Default VAT
- **WHEN** a source price is 100 EUR/MWh and VAT is 24%
- **THEN** the display price is 12.4 senti/kWh

#### Scenario: Negative price
- **WHEN** a source price is negative
- **THEN** the display price is the same conversion, remaining negative

### Requirement: Missing or failed price data is explicit
If Elering Live is unreachable, returns an unsuccessful payload, or returns no EE intervals for the requested day, the system SHALL treat that day as unavailable rather than inventing prices.

#### Scenario: Empty day
- **WHEN** the request for today’s EE series returns no intervals
- **THEN** that day is unavailable

#### Scenario: Transport failure
- **WHEN** the Elering request fails
- **THEN** that day is unavailable
