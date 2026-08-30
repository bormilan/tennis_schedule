# Simple ATP Match Email Script — Implementation Plan

## Goal

Build one small Python script that fetches upcoming ATP men's singles matches from API-Tennis and emails a readable HTML digest to one recipient.

## Scope

- ATP Singles only.
10. Write logs to stderr and to `atp_digest.log` by default; fail clearly if the log file cannot be opened.
- One API request per run.
- One recipient.
- One HTML email with a plain-text fallback.

## Runtime behavior

1. Load configuration from environment variables, optionally using the local `.env` file.
2. Calculate today and the end date using `TIMEZONE` and `LOOKAHEAD_DAYS`.
3. Call API-Tennis `get_fixtures` with the API key, date range, `event_type_key=265` for `Atp Singles`, and the configured timezone.
4. Keep records that are ATP Singles, have both player names and a scheduled date/time, are not live, and are scheduled from now through the end of the requested window.
5. Sort matches by local start time.
6. Render a simple self-contained HTML email grouped by date.
7. Send it through authenticated SMTP to `EMAIL_TO`.
8. Exit with a non-zero status and a short error message if configuration, API, parsing, or email delivery fails.
9. Log each major stage and every failure without logging secrets.

## Implementation shape

- `atp_digest.py`: configuration, API request, filtering, rendering, and email delivery in one small file.
- `.env.example`: configuration template with placeholders only.
- `requirements.txt`: only the small runtime dependencies.
- `LOGGING.md`: logging behavior, security rules, and logging tests.
- No database, web server, frontend build, template system, API event discovery, live polling, odds, predictions, persistence.

## Email design

- Subject: `Upcoming ATP matches — YYYY-MM-DD to YYYY-MM-DD`.
- Title, covered date range, timezone, and generated timestamp.
- Each match shows local time, tournament, round when available, and both players.
- Matches are grouped by local date.
- A clear `No upcoming ATP matches` empty state is sent when the API returns none.
- All API text is HTML-escaped.

## Implementation steps

1. Add `atp_digest.py` with environment validation and one `requests.get` call.
2. Parse the documented fixture fields and apply the ATP/future-match filter.
3. Add small HTML and plain-text render functions using the standard library.
4. Add standard-library SMTP delivery with STARTTLS.
5. Add one short README section covering environment setup and running the script.
6. Test one successful run, one empty result, and one failed API or SMTP connection.

## Acceptance criteria

- A normal run fetches ATP Singles fixtures and sends one email to `EMAIL_TO`.
- No Challenger, ITF, doubles, women's, junior, live, or completed matches appear.
- The email contains the correct local time, tournament, round when available, and player names.
- Missing optional fields do not crash the run.
- Secrets are only read from environment variables and never logged.
- A failed run is visible through a non-zero exit status.
- A failed run produces an actionable error log.
- A normal run writes the same log messages to stderr and the default log file.

## Fixed decisions

- Match scope is ATP Singles only.
- API event type key is `265`, based on the API-Tennis documentation example for `Atp Singles`.
- The default window is today plus the next 7 calendar days.
- The default display timezone is UTC.
