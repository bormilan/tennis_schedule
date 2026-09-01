import io
import logging
from datetime import datetime, timezone
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from unittest.mock import Mock, patch

import requests

from atp_digest import APIError, ConfigError, LOGGER_NAME, fetch_matches, load_config, setup_logging


class ConfigAndLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = {
            "API_TENNIS_API_KEY": "api-key-for-tests",
            "EMAIL_TO": "recipient@example.com",
            "EMAIL_FROM": "sender@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "smtp-user",
            "SMTP_PASSWORD": "smtp-password-for-tests",
            "SMTP_USE_TLS": "true",
            "TIMEZONE": "UTC",
            "LOOKAHEAD_DAYS": "7",
            "API_TIMEOUT_SECONDS": "30",
            "LOG_LEVEL": "INFO",
            "LOG_FILE": str(Path(self.temp_dir.name) / "atp_digest.log"),
        }

    def tearDown(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        self.temp_dir.cleanup()

    def test_valid_configuration_is_loaded(self) -> None:
        config = load_config(self.env, load_env_file=False)

        self.assertEqual(config.email_to, "recipient@example.com")
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.lookahead_days, 7)
        self.assertEqual(config.log_level, "INFO")

    def test_missing_api_key_fails(self) -> None:
        self.env.pop("API_TENNIS_API_KEY")

        with self.assertRaisesRegex(ConfigError, "API_TENNIS_API_KEY"):
            load_config(self.env, load_env_file=False)

    def test_missing_email_to_fails(self) -> None:
        self.env.pop("EMAIL_TO")

        with self.assertRaisesRegex(ConfigError, "EMAIL_TO"):
            load_config(self.env, load_env_file=False)

    def test_invalid_email_to_fails(self) -> None:
        self.env["EMAIL_TO"] = "not-an-email"

        with self.assertRaisesRegex(ConfigError, "EMAIL_TO"):
            load_config(self.env, load_env_file=False)

    def test_invalid_numeric_setting_fails(self) -> None:
        self.env["SMTP_PORT"] = "not-a-port"

        with self.assertRaisesRegex(ConfigError, "SMTP_PORT"):
            load_config(self.env, load_env_file=False)

    def test_invalid_timezone_fails(self) -> None:
        self.env["TIMEZONE"] = "Not/A_Timezone"

        with self.assertRaisesRegex(ConfigError, "TIMEZONE"):
            load_config(self.env, load_env_file=False)

    def test_logging_writes_to_stderr_and_file(self) -> None:
        config = load_config(self.env, load_env_file=False)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            logger = setup_logging(config)
            logger.info("selected 0 matches")

        file_output = config.log_file.read_text(encoding="utf-8")
        self.assertIn("selected 0 matches", stderr.getvalue())
        self.assertIn("selected 0 matches", file_output)
        self.assertIn("INFO", file_output)

    def test_log_file_failure_is_reported_without_secret(self) -> None:
        self.env["LOG_FILE"] = str(Path(self.temp_dir.name) / "missing" / "atp_digest.log")
        config = load_config(self.env, load_env_file=False)
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaisesRegex(ConfigError, "LOG_FILE"):
            setup_logging(config)

        self.assertIn("logging setup failed", stderr.getvalue())
        self.assertNotIn(self.env["SMTP_PASSWORD"], stderr.getvalue())
        self.assertNotIn(self.env["API_TENNIS_API_KEY"], stderr.getvalue())


    def test_fetch_uses_exact_request_parameters(self) -> None:
        config = load_config(self.env, load_env_file=False)
        fixtures = [{"event_key": "123", "event_status": "Not Started"}]
        response = Mock()
        response.json.return_value = {"success": 1, "result": fixtures}
        current = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)

        with patch("atp_digest.requests.get", return_value=response) as get:
            self.assertEqual(fetch_matches(config, now=current), fixtures)

        get.assert_called_once_with(
            config.api_base_url,
            params={
                "method": "get_fixtures",
                "APIkey": self.env["API_TENNIS_API_KEY"],
                "date_start": "2026-09-01",
                "date_stop": "2026-09-08",
                "event_type_key": 265,
                "timezone": "UTC",
            },
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()

    def test_fetch_accepts_empty_results(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock()
        response.json.return_value = {"success": 1, "result": []}

        with patch("atp_digest.requests.get", return_value=response):
            self.assertEqual(
                fetch_matches(
                    config,
                    now=datetime(2026, 9, 1, 12, tzinfo=timezone.utc),
                ),
                [],
            )

    def test_fetch_rejects_http_failure_without_secret(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock(status_code=503)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)

        with patch("atp_digest.requests.get", return_value=response):
            with self.assertLogs(LOGGER_NAME, level="ERROR") as captured:
                with self.assertRaisesRegex(APIError, "API request failed"):
                    fetch_matches(config)

        output = "\n".join(captured.output)
        self.assertIn("HTTP status 503", output)
        self.assertNotIn(self.env["API_TENNIS_API_KEY"], output)

    def test_fetch_rejects_timeout(self) -> None:
        config = load_config(self.env, load_env_file=False)

        with patch("atp_digest.requests.get", side_effect=requests.Timeout):
            with self.assertLogs(LOGGER_NAME, level="ERROR") as captured:
                with self.assertRaisesRegex(APIError, "timed out"):
                    fetch_matches(config)

        self.assertIn("timed out after 30 seconds", "\n".join(captured.output))

    def test_fetch_rejects_invalid_json(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock()
        response.json.side_effect = ValueError

        with patch("atp_digest.requests.get", return_value=response):
            with self.assertRaisesRegex(APIError, "valid JSON"):
                fetch_matches(config)

    def test_fetch_rejects_unsuccessful_api_response(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock()
        response.json.return_value = {"success": 0, "result": []}

        with patch("atp_digest.requests.get", return_value=response):
            with self.assertRaisesRegex(APIError, "unsuccessful"):
                fetch_matches(config)

    def test_fetch_rejects_missing_result(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock()
        response.json.return_value = {"success": 1}

        with patch("atp_digest.requests.get", return_value=response):
            with self.assertRaisesRegex(APIError, "result was not a list"):
                fetch_matches(config)

    def test_fetch_rejects_non_list_result(self) -> None:
        config = load_config(self.env, load_env_file=False)
        response = Mock()
        response.json.return_value = {"success": 1, "result": {}}

        with patch("atp_digest.requests.get", return_value=response):
            with self.assertRaisesRegex(APIError, "result was not a list"):
                fetch_matches(config)


if __name__ == "__main__":
    unittest.main()
