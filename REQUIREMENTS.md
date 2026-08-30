# Requirements — Upcoming Men's Singles Email Digest

## 1. Functional requirements

### FR-1: Configuration

The script MUST read secrets and runtime settings from environment variables. It MUST fail fast with a clear message when a required variable is missing or invalid.

Required variables:

- `API_TENNIS_API_KEY`: API-Tennis account key.
- `EMAIL_TO`: recipient email address. Put your own email address here in the local `.env` file.
- `EMAIL_FROM`: sender address accepted by the SMTP account.
- `SMTP_HOST`: SMTP server hostname.
- `SMTP_PORT`: SMTP server port, normally `587` for STARTTLS or `465` for implicit TLS.
- `SMTP_USERNAME`: SMTP login username.
- `SMTP_PASSWORD`: SMTP login password or provider app password.

Optional variables and defaults:

- `TIMEZONE=UTC`: IANA timezone used for date boundaries and display.
- `LOOKAHEAD_DAYS=7`: number of future calendar days to include after today; must be a non-negative integer.
- `MEN_SINGLES_EVENT_TYPES=Atp Singles`: event type names to include. Matching is case-insensitive after trimming whitespace.
- `API_TENNIS_BASE_URL=https://api.api-tennis.com/tennis/`: API base URL.
- `API_TIMEOUT_SECONDS=30`: per-request timeout.
- `API_MAX_RETRIES=2`: bounded retry count for transient network/5xx failures.
- `SMTP_USE_TLS=true`: use STARTTLS when `true`; do not combine with implicit TLS on port 465 without an explicit implementation decision.
- `EMAIL_SUBJECT_PREFIX=Upcoming men's singles matches`: subject prefix.

The repository MUST include `.env.example` with placeholders only. A real `.env` file MUST be ignored by version control when a repository is added.

### FR-2: Discover and fetch fixtures

1. Call API-Tennis `get_events` using `API_TENNIS_API_KEY`.
2. Resolve the configured event type names to `event_type_key` values returned by the API.
3. Call `get_fixtures` for each resolved event type with:
   - `date_start`: today in `TIMEZONE`.
   - `date_stop`: today plus `LOOKAHEAD_DAYS` calendar days in `TIMEZONE`.
4. Include the API timezone or an explicitly supported timezone parameter if the chosen API response supports it; otherwise parse the returned scheduled timestamp as documented by the provider and convert it safely.
5. Do not request or expose API credentials in the generated page or email.

The source API reference is the API-Tennis [documentation](https://api-tennis.com/documentation). The documented fixtures method uses `get_fixtures`, `date_start`, `date_stop`, and optional `event_type_key`; the documented events method provides event type keys such as `Atp Singles`.

### FR-3: Select upcoming men's singles matches

The script MUST:

- Include only records belonging to the configured men's singles event types.
- Exclude doubles, women's, junior, exhibition, and other event types unless explicitly configured.
- Exclude matches whose normalized status is completed, cancelled, postponed without a scheduled time, or live.
- Include matches with a future scheduled time within the requested inclusive window.
- Deduplicate by stable `match_key` when present; use a deterministic composite key only when the API omits it.
- Sort ascending by scheduled time, then tournament name, round, and player names.
- Tolerate optional/missing round, ranking, country, or status fields.

### FR-4: Render the match page/digest

The output MUST be a self-contained HTML email page with:

- A clear title and covered date range.
- Generation timestamp and configured timezone.
- Matches grouped by local date and tournament.
- For each match: local start time, tournament, round when available, event type when useful, and both player names.
- A responsive layout that remains usable on desktop and mobile email clients.
- HTML escaping for every value originating from the API or environment.
- A meaningful empty state when no matches are found.

The message MUST also include a plain-text alternative containing the same essential match information.

### FR-5: Send the email

The script MUST:

- Send a `multipart/alternative` email with the HTML and plain-text versions.
- Use `EMAIL_TO`, `EMAIL_FROM`, and SMTP variables from the environment.
- Use authenticated SMTP and STARTTLS by default.
- Use a subject containing the date range.
- Close the SMTP connection cleanly.
- Return a non-zero process exit code if sending fails.

### FR-6: CLI and scheduling

The script MUST support:

- Normal mode: fetch, render, and send.
- `--dry-run`: fetch and render without sending; print or write the output for inspection.
- `--version` or equivalent basic help output.

Scheduling MUST be external to the script. Documentation MUST include a sample daily cron/systemd-style invocation and explain that the environment must be available to the scheduled process.

## 2. Non-functional requirements

- Python 3.11+.
- Use a small dependency footprint: HTTP client, `.env` loader, and standard-library email/SMTP and timezone support where practical.
- All network requests MUST have a timeout.
- Retries MUST be bounded and MUST NOT retry authentication or validation failures.
- Logs MUST be useful for diagnosis but MUST NOT contain API keys, SMTP passwords, or full message bodies.
- The script MUST be deterministic for the same API response, configuration, and current date/time.
- Secrets MUST be supplied at runtime and MUST NOT be committed.
- The code SHOULD use type hints and clear separation between fetching, normalization, rendering, and sending.

## 3. Test requirements

Automated tests MUST cover:

- Successful event discovery and fixture requests.
- Multiple event types and correct men's-singles filtering.
- Inclusive date-window boundaries and timezone conversion.
- Exclusion of completed/live/non-men's-singles matches.
- Deduplication and deterministic sorting.
- HTML escaping and plain-text generation.
- Empty fixture results.
- API non-success responses, malformed payloads, timeout, and retry exhaustion.
- Missing/invalid environment variables.
- SMTP authentication or connection failure.
- `--dry-run` not sending email.

## 4. Initial dependency requirements

The initial implementation may use:

- `requests` for HTTPS API calls.
- `python-dotenv` for local `.env` loading.

Email, HTML escaping, command-line parsing, logging, and timezone handling should use the Python standard library (`email`, `smtplib`, `html`, `argparse`, `logging`, and `zoneinfo`) unless implementation testing shows a strong reason to add another dependency.

## 5. Out of scope for version 1

- Betting odds, predictions, player rankings, head-to-head history, or news.
- Live score polling or WebSocket subscriptions.
- A web server or permanently hosted public page.
- User accounts, multiple recipients, unsubscribe management, or a database.
- Automatic scheduler installation.
