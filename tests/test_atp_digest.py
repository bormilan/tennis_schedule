import io
import logging
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from atp_digest import ConfigError, LOGGER_NAME, load_config, setup_logging


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


if __name__ == "__main__":
    unittest.main()
