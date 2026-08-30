# Test Plan — Simple ATP Match Email Script

## Purpose

Verify that the script fetches only upcoming ATP Singles matches, renders the expected email, and sends it through SMTP. Tests must remain small and must not call the real API or send real email.

## Test approach

- Use Python standard-library `unittest` and `unittest.mock`.
- Put tests in `tests/test_atp_digest.py` once `atp_digest.py` is implemented.
- Mock HTTP and SMTP boundaries.
- Use fixed datetimes and representative API response dictionaries.
- Do not require API keys, SMTP credentials, network access, or a live mailbox.

## Test cases

### Configuration

- Missing `API_TENNIS_API_KEY` fails clearly.
- Missing `EMAIL_TO` fails clearly.
- Missing SMTP settings fails clearly.
- Invalid `LOOKAHEAD_DAYS`, `SMTP_PORT`, or `TIMEZONE` fails clearly.
- A complete environment produces a valid configuration.

### API request

Mock `requests.get` and verify:

- The request uses `get_fixtures`.
- `event_type_key=265` is sent for `Atp Singles`.
- `date_start`, `date_stop`, and `timezone` are correct.
- The configured timeout is passed.
- A non-success API response fails clearly.
- Invalid JSON fails clearly.
- A response without a result list fails clearly.
- An empty result list is accepted.

### Match filtering

| Fixture | Expected result |
|---|---|
| Future ATP Singles match | Included |
| Challenger match | Excluded |
| ITF match | Excluded |
| Doubles match | Excluded |
| Live match | Excluded |
| Completed or past match | Excluded |
| Missing player name | Excluded |
| Missing or invalid date/time | Excluded |
| Duplicate `event_key` | Included once |
| Several valid matches | Sorted by local start time |

Also test timezone conversion and the start/end date boundaries.

### Email rendering

- Player names, tournament, round, local time, and date appear in the HTML.
- The plain-text part contains the same essential match information.
- Empty results render `No upcoming ATP matches`.
- API text such as `<script>alert(1)</script>` is HTML-escaped.
- The subject contains the requested date range.
- API keys and SMTP passwords never appear in the output.

### SMTP delivery

Use a fake SMTP client and verify:

- The SMTP connection is opened.
- STARTTLS is called when enabled.
- Configured credentials are used for login.
- The message is sent to `EMAIL_TO` from `EMAIL_FROM`.
- The message is multipart/alternative.
- SMTP errors fail clearly and return a non-zero result.
- The connection is closed cleanly.

### Logging

- Missing or invalid `EMAIL_TO` produces an `ERROR` log.
- API failure produces an `ERROR` log without the API key.
- SMTP failure produces an `ERROR` log without the SMTP password.
- Unexpected exceptions include a traceback.
- Successful runs log the selected match count and successful delivery.
- A writable `LOG_FILE` receives the same messages sent to stderr.
### End-to-end orchestration

Mock the API and SMTP together:

1. Load configuration.
2. Fetch one ATP match.
3. Filter the response.
4. Render HTML and plain text.
5. Send one email.
6. Verify the recipient, subject, player names, and email body.

## Suggested script boundaries

Keep the implementation easy to test with these small functions:

```text
load_config()
fetch_matches()
filter_matches()
render_email()
send_email()
```

## Test command

Use the standard library test runner:

```bash
python -m unittest discover -s tests -v
```
