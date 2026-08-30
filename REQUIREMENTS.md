# Requirements — Simple ATP Match Email Script

## Purpose

The project is a narrow utility, not a general tennis application. It fetches upcoming ATP men singles matches and sends one email digest to one configured recipient.

## Required runtime

- Python 3.11 or newer.
- One executable script: `atp_digest.py`.
- Dependencies: `requests` and `python-dotenv`.

## Environment variables

Required:

- `API_TENNIS_API_KEY`: API-Tennis API key.
- `EMAIL_TO`: the recipient email address.
- `EMAIL_FROM`: the verified sender email address.
- `SMTP_HOST`: SMTP server hostname.
- `SMTP_PORT`: SMTP port.
- `SMTP_USERNAME`: SMTP username.
- `SMTP_PASSWORD`: SMTP password, app password, or SMTP key.

Optional:

- `TIMEZONE=UTC`: IANA timezone used for date boundaries and display.
- `LOOKAHEAD_DAYS=7`: number of calendar days after today to include.
- `API_TENNIS_BASE_URL=https://api.api-tennis.com/tennis/`: API base URL.
- `API_TIMEOUT_SECONDS=30`: request timeout.
- `SMTP_USE_TLS=true`: use STARTTLS on the SMTP connection.
- `LOG_LEVEL=INFO`: logging level.
- `LOG_FILE=atp_digest.log`: persistent log file path; logs also always go to stderr.

The repository must contain `.env.example` with placeholders and must never contain a real `.env` file or secret.

## Logging

The script must configure Python standard-library logging. It must always write logs to stderr and also write them to `LOG_FILE` (default `atp_digest.log`). `INFO` logs should identify the run stages and selected match count. Configuration, API, parsing, and SMTP failures must be logged at `ERROR` level, and unexpected exceptions must include a traceback.

The process must exit non-zero after any failure, including when the log file cannot be opened. Logs must never include API keys, SMTP passwords, full API responses, or full email bodies.
## API request

The script must make one `GET` request to API-Tennis `get_fixtures` with:

- `method=get_fixtures`
- `APIkey` from `API_TENNIS_API_KEY`
- `date_start` equal to today in `TIMEZONE`
- `date_stop` equal to today plus `LOOKAHEAD_DAYS`
- `event_type_key=265` for `Atp Singles`
- `timezone` from `TIMEZONE`

The documented response fields to use are `event_key`, `event_date`, `event_time`, `event_first_player`, `event_second_player`, `event_status`, `event_type_type`, `tournament_name`, `tournament_round`, and `event_live`.

The script must fail clearly when the API returns a non-success response, invalid JSON, or a response without a result list. It should use the configured timeout. No event discovery or retry framework is needed.

## Match filtering

Keep a match only when:

- `event_type_type` is `Atp Singles`, case-insensitively.
- It has two player names and a parseable date/time.
- `event_live` is not `1` or `true`.
- Its scheduled time is now or later and falls within the requested window.

Deduplicate by `event_key` and sort by scheduled local time. Optional round, tournament, status, and key fields must not crash the script.

## Email output

Send one `multipart/alternative` message through authenticated SMTP:

- HTML part: a self-contained, mobile-readable page grouped by local date.
- Plain-text part: the same essential match information.
- Subject: `Upcoming ATP matches — YYYY-MM-DD to YYYY-MM-DD`.
- Each match: local start time, tournament, round when available, and both players.
- Empty result: send `No upcoming ATP matches` instead of failing.
- Escape all API-provided values before placing them in HTML.

Use STARTTLS by default and close the SMTP connection cleanly. Do not log API keys, SMTP passwords, or full email bodies.

## Command behavior

Running `python atp_digest.py` must fetch, render, and send the digest. No additional application services or interactive modes are required.


## Minimal verification

Before considering the script complete, verify:

- a normal response produces an email;
- an empty response produces the empty-state email;
- non-ATP records are excluded;
- completed or live records are excluded;
- HTML values are escaped;
- missing required environment variables fail clearly;
- API or SMTP failure exits non-zero.

## Out of scope

- Challenger, ITF, WTA, junior, exhibition, or doubles matches.
- API event discovery.
- Odds, rankings, predictions, news, scores, or notifications beyond the single digest.
- Multiple users or recipients.
- Persistent storage or a hosted website.
