# Logging — Simple ATP Match Email Script

## Goal

The script must make failures visible when it is run manually or from any automated invocation. A failed API request, invalid `EMAIL_TO`, or SMTP delivery error must never disappear silently.

## Simple design

- Use Python's standard-library `logging` module.
- Log `INFO` messages to show the normal stages of a run.
- Log expected failures at `ERROR` level.
- Log unexpected failures with `logger.exception(...)` so a traceback is available.
- Always write logs to stderr.
- If `LOG_FILE` is configured, also write the same messages to that file.
- Use `LOG_LEVEL=INFO` by default; allow `DEBUG` when diagnosing a problem.
- Keep the process exit status non-zero after any configuration, API, parsing, or email-delivery failure.

## Environment variables

- `LOG_LEVEL=INFO`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.
- `LOG_FILE=`: optional path for a persistent log file. Leave empty to use stderr only.

The logger should fall back to stderr if the configured log file cannot be opened, and should report that fallback as a warning.

## Events to log

At `INFO` level:

- Script started.
- Requested ATP fixture date window and timezone.
- Number of fixture records received.
- Number of upcoming ATP matches selected.
- Email sent successfully.

At `ERROR` level:

- Required configuration is missing or invalid, including `EMAIL_TO`.
- API request timed out or returned an unsuccessful response.
- API response is malformed.
- Match date/time cannot be parsed.
- SMTP connection, authentication, or message delivery failed.

Error messages should identify the failed stage and a useful cause, for example:

```text
ERROR email delivery failed: SMTP authentication failed
ERROR invalid configuration: EMAIL_TO is missing or invalid
ERROR API request failed: request timed out after 30 seconds
```

## Security rules

Never log:

- `API_TENNIS_API_KEY`.
- `SMTP_PASSWORD` or an SMTP/app key.
- Full API responses.
- Full HTML or plain-text email bodies.

Logging a sanitized hostname, port, status code, match count, or error type is acceptable. Email addresses should not be included in error messages unless needed for local diagnosis.

## Tests

The test suite should capture logs and verify:

- Missing or invalid `EMAIL_TO` produces an `ERROR` log.
- API failure produces an `ERROR` log without the API key.
- SMTP failure produces an `ERROR` log without the SMTP password.
- An unexpected exception produces a traceback through `logger.exception`.
- A successful run logs the selected match count and successful delivery.
- The configured `LOG_FILE` receives messages when it is writable.
