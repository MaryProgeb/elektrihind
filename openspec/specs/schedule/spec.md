# schedule Specification

## Purpose

Runs a single remaining-today send at 08:00 Europe/Tallinn. Tomorrow is out of scope.

## Requirements

### Requirement: Daily run covers remaining today from 08:00
At 08:00 Europe/Tallinn the system SHALL evaluate remaining today from 08:00 local time and send the daily message. If the job starts later, already-started intervals MUST still be excluded. The run MUST NOT fetch or compare tomorrow.

#### Scenario: On-time daily job
- **WHEN** the command runs at 08:00 Europe/Tallinn
- **THEN** slots are selected from 08:00 onward today and the daily message is sent

#### Scenario: Late job
- **WHEN** the command runs at 08:20
- **THEN** intervals that started before 08:20 are excluded

#### Scenario: Tomorrow is not requested
- **WHEN** the daily command runs
- **THEN** the system does not request prices for the next calendar day

### Requirement: CLI entry point
The system SHALL expose `python -m elektrihind` for the remaining-today flow. It MUST NOT require a `today` or `tomorrow` subcommand.

#### Scenario: Default command
- **WHEN** `python -m elektrihind` is invoked
- **THEN** it performs the remaining-today 08:00 flow

### Requirement: Afternoon notification waits for tomorrow's published prices
The afternoon run SHALL evaluate prices from 15:00 Europe/Tallinn today through the end of the next local calendar day. It SHALL begin at 15:07 when scheduled and retry Elering every five minutes while the complete next-day series is unavailable, stopping when the series is available or at 18:00 local time. It MUST send no partial message; if the series is still unavailable at the deadline, the run MUST send nothing and exit unsuccessfully. The afternoon command MAY be manually dispatched and SHALL apply the same availability and no-partial-send rules.

#### Scenario: Tomorrow is available on the first poll
- **WHEN** the afternoon run finds the complete next-day EE series
- **THEN** it evaluates the afternoon span and sends one message without waiting for another poll

#### Scenario: Scheduled run starts at 15:07
- **WHEN** the scheduled afternoon run starts at 15:07 and prices are already complete
- **THEN** it sends on the first poll and excludes the 15:00 interval from slot candidates, whose earliest possible start is 15:15

#### Scenario: Tomorrow is published during polling
- **WHEN** a poll before 18:00 finds tomorrow's series incomplete and a later poll finds it complete
- **THEN** the run sends one message using the complete afternoon span

#### Scenario: Tomorrow remains unavailable at the deadline
- **WHEN** the 18:00 Europe/Tallinn deadline is reached without a complete next-day series
- **THEN** the run sends no message and exits unsuccessfully

#### Scenario: Final poll is bounded by the deadline
- **WHEN** the previous five-minute poll occurs before 18:00
- **THEN** the run waits only until 18:00 for its final fetch and does not poll or send after that deadline

### Requirement: Morning and afternoon notifications are hosted separately
Deployment SHALL retain the existing morning GitHub Actions workflow and add a separate afternoon workflow. The morning workflow SHALL continue to trigger at 08:07 Europe/Tallinn and run `python -m elektrihind`; the afternoon workflow SHALL trigger at 15:07 Europe/Tallinn and run `python -m elektrihind afternoon`. Both workflows SHALL support `workflow_dispatch`. Telegram secrets MUST come from GitHub Actions secrets, not git. The workflows MUST NOT use Docker or open a public HTTP port. Missed or dropped scheduled runs MUST NOT be replayed automatically.

#### Scenario: Morning schedule remains unchanged
- **WHEN** the morning schedule runs at 08:07 Europe/Tallinn
- **THEN** it invokes `python -m elektrihind` and performs the existing remaining-today flow

#### Scenario: Afternoon schedule starts the afternoon flow
- **WHEN** the afternoon schedule runs at 15:07 Europe/Tallinn
- **THEN** it invokes `python -m elektrihind afternoon` with Telegram secrets from GitHub Actions

#### Scenario: Manual afternoon retry
- **WHEN** a user dispatches the afternoon workflow manually
- **THEN** it runs the same afternoon flow and applies the same polling deadline and availability rules

#### Scenario: Manual morning retry
- **WHEN** a user dispatches the morning workflow manually
- **THEN** it performs the existing remaining-today flow

#### Scenario: Hosted without a container or public port
- **WHEN** both scheduled workflows are installed
- **THEN** they run on GitHub-hosted runners without Docker and listen on no public HTTP port

#### Scenario: Missed schedule is not replayed
- **WHEN** GitHub delays or drops either scheduled run
- **THEN** the system does not run a catch-up job on its own
