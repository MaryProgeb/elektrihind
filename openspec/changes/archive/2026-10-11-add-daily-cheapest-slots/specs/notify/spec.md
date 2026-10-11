# Spec Delta

## Purpose

Formats one Estonian Telegram message for today’s cheapest 3-hour slots and posts it to a configured channel.

## ADDED Requirements

### Requirement: Messages are Estonian with VAT-inclusive senti
User-facing messages SHALL be in Estonian. Slot prices and day averages SHALL be shown as senti/kWh including configured VAT, rounded to one decimal place, with no network fee or excise.

#### Scenario: Slot line
- **WHEN** a window is 11:15–14:15 with display mean 4.21 senti/kWh
- **THEN** the message includes a line equivalent to `11:15–14:15` and `4.2 s/kWh`

### Requirement: Message lists remaining-today slots
The 08:00 message SHALL state that it covers today from 08:00, list the selected windows cheapest-first with local start–end and display mean, and include the mean of the remaining-today series as `Päeva keskmine`. The message MUST NOT mention tomorrow or advise waiting.

#### Scenario: Three slots available
- **WHEN** three remaining-today windows were selected
- **THEN** the message lists all three numbered 1–3 and includes `Päeva keskmine`

#### Scenario: Remaining day too short
- **WHEN** no remaining-today window exists
- **THEN** the message says remaining today is too short for a 3-hour window and lists no invented slots

#### Scenario: Tomorrow is absent
- **WHEN** the daily message is composed
- **THEN** it contains no tomorrow prices, skip advice, or unpublished-tomorrow text

### Requirement: Posts go to the configured Telegram channel
The system SHALL post via Telegram Bot API using `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Those values MUST come from the environment and MUST NOT be committed to git.

#### Scenario: Channel send
- **WHEN** a message is ready and token and chat id are set
- **THEN** the bot sends that text to the configured chat

#### Scenario: Missing secrets
- **WHEN** token or chat id is unset
- **THEN** the system does not send and reports the configuration error
