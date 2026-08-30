# Upcoming Men's Singles Email Digest — Implementation Plan

## Goal

Build a small scheduled Python script that retrieves upcoming men's singles tennis matches from API-Tennis, renders them as a readable HTML digest, and sends the digest by email.

## Working assumptions

- “Men's singles” means ATP Singles only (`Atp Singles`).
- The default lookahead window is today through the next 7 calendar days, inclusive.
- Match times are displayed in the configured `TIMEZONE` (default: `UTC`).
- The script sends one digest per run; scheduling is handled externally by cron, systemd, GitHub Actions, or another scheduler.
- No match odds, predictions, live polling, or persistence are required for the first version.

## Proposed components

1. **Configuration**
   - Load settings from environment variables, optionally through a local `.env` file.
   - Validate required API, recipient, sender, and SMTP settings before making requests.

2. **API client**
   - Call `get_events` to discover the account’s available event types.
   - Select configured men's singles event types and obtain their `event_type_key` values.
   - Call `get_fixtures` for the configured date window, once per selected event type.
   - Treat non-success API responses, timeouts, malformed JSON, and unavailable event types as actionable errors.

3. **Match normalization and filtering**
   - Normalize API records into an internal match model containing match key, tournament, round, scheduled time, player names, event type, and status.
   - Keep only matches scheduled in the requested future window and exclude completed, cancelled, live, doubles, women's, and junior matches.
   - Deduplicate records by `match_key` and sort by local scheduled time, tournament, and player names.
   - Preserve missing values as an em dash rather than failing the entire digest.

4. **HTML rendering**
   - Group matches by local calendar date, then by tournament.
   - Render responsive email-safe HTML with a title, generated-at timestamp, match cards/table rows, tournament, round, local time, and both players.
   - Escape all API-provided text before inserting it into HTML.
   - Render an explicit empty-state message when no upcoming matches are returned.
   - Produce a plain-text alternative for email clients that do not support HTML.

5. **Email delivery**
   - Send a multipart/alternative message through authenticated SMTP using STARTTLS by default.
   - Use `EMAIL_TO` for the recipient and `EMAIL_FROM` for the sender.
   - Set a deterministic subject containing the date range, for example: `Upcoming men's singles matches — 2026-08-30 to 2026-09-06`.

6. **Operations and scheduling**
   - Exit non-zero on configuration, API, rendering, or email failures.
   - Log useful diagnostics without logging API keys, SMTP passwords, or full email contents.
   - Add a command-line entry point with `--dry-run` to render and print/save the digest without sending it.
   - Provide an example cron invocation and document the expected scheduler behavior.

## Implementation sequence

1. Create the Python package/entry point and configuration validation.
2. Implement the API-Tennis client with request timeout, bounded retries for transient failures, and response validation.
3. Implement event-type selection, fixture normalization, future filtering, deduplication, and sorting.
4. Add HTML and plain-text templates with escaping and empty-state behavior.
5. Add SMTP delivery and dry-run mode.
6. Add unit tests using saved representative API responses and a fake SMTP server/client.
7. Add a README with setup, `.env` configuration, local execution, dry-run usage, and scheduling.
8. Run formatting, static checks, and the test suite; then verify one end-to-end run with credentials supplied through the environment.

## Acceptance criteria

- A configured run fetches only upcoming men's singles fixtures for the requested date window.
- The email includes every eligible match exactly once, with correct local date/time, tournament, round when available, and both player names.
- The email remains readable on narrow screens and includes a plain-text fallback.
- API failures, SMTP failures, invalid configuration, and malformed records produce a clear log message and non-zero exit status.
- Secrets are never committed, printed, or embedded in generated HTML.
- A no-matches run still sends a useful empty digest unless a future configuration option explicitly disables it.
- Tests cover event filtering, date/time conversion, deduplication, HTML escaping, empty results, API errors, and SMTP errors.

## Open decisions for implementation

- The event type remains configurable for future expansion, but the required and default scope is ATP Singles only.
- Whether the digest should be sent every day or at another cadence. This belongs to the external scheduler.
- Which SMTP provider/account will send the message. The implementation will use standard SMTP settings so the provider can be chosen later.
