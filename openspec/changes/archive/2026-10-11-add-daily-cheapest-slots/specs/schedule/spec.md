# Spec Delta

## Purpose

Runs a single remaining-today send at 08:00 Europe/Tallinn. Tomorrow is out of scope.

## ADDED Requirements

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

### Requirement: Hosted on one GitHub Actions workflow without Docker
Deployment SHALL use one GitHub Actions workflow on the default branch that runs `python -m elektrihind`. It SHALL trigger on a daily `schedule` at 08:07 Europe/Tallinn (`cron: '7 8 * * *'` with `timezone: Europe/Tallinn`) and on `workflow_dispatch`. Secrets MUST come from GitHub Actions secrets, not from git. The workflow MUST NOT use Docker or open a public HTTP port. A missed or dropped schedule MUST NOT be replayed automatically.

#### Scenario: Daily schedule
- **WHEN** the scheduled workflow runs at 08:07 Europe/Tallinn
- **THEN** it invokes `python -m elektrihind` with token and chat id from secrets

#### Scenario: Manual retry
- **WHEN** a user starts the workflow with `workflow_dispatch`
- **THEN** it performs the same remaining-today send as the scheduled run

#### Scenario: Missed schedule is not replayed
- **WHEN** GitHub delays or drops the scheduled run
- **THEN** the system does not run a catch-up job on its own

#### Scenario: No container and no public port
- **WHEN** the workflow is installed as specified
- **THEN** it runs on a GitHub-hosted runner without Docker and listens on no public HTTP port
