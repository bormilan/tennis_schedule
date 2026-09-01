"""Configuration and logging foundation for the ATP match digest."""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping, cast
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv


LOGGER_NAME = "atp_digest"
DEFAULT_API_BASE_URL = "https://api.api-tennis.com/tennis/"
DEFAULT_LOG_FILE = "atp_digest.log"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+$")
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


class APIError(RuntimeError):
    """Raised when the API request or response cannot be used."""


@dataclass(frozen=True)
class Config:
    """Validated runtime configuration.

    API and SMTP operations are intentionally implemented in later tasks.
    """

    api_key: str
    api_base_url: str
    email_to: str
    email_from: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    timezone: str
    lookahead_days: int
    api_timeout_seconds: int
    log_level: str
    log_file: Path


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def _email(environ: Mapping[str, str], name: str) -> str:
    value = _required(environ, name)
    if not EMAIL_PATTERN.fullmatch(value):
        raise ConfigError(f"{name} is invalid")
    return value


def _integer(environ: Mapping[str, str], name: str, default: int, *, minimum: int, maximum: int | None = None) -> int:
    raw = environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be at most {maximum}")
    return value


def _boolean(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = environ.get(name, str(default)).strip().lower()
    if raw in {"true", "1", "yes"}:
        return True
    if raw in {"false", "0", "no"}:
        return False
    raise ConfigError(f"{name} must be true or false")


def _timezone(environ: Mapping[str, str]) -> str:
    value = environ.get("TIMEZONE", "UTC").strip()
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"TIMEZONE is invalid: {value}") from exc
    return value


def _api_url(environ: Mapping[str, str]) -> str:
    value = environ.get("API_TENNIS_BASE_URL", DEFAULT_API_BASE_URL).strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("API_TENNIS_BASE_URL must be an HTTP or HTTPS URL")
    return value


def load_config(
    environ: Mapping[str, str] | None = None,
    *,
    load_env_file: bool = True,
) -> Config:
    """Load and validate environment configuration.

    Tests can pass an explicit mapping and disable `.env` loading. Secrets are
    stored only in the returned object and are never included in errors.
    """

    if environ is None:
        if load_env_file:
            load_dotenv()
        values = dict(os.environ)
    else:
        values = dict(environ)

    log_level = values.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in ALLOWED_LOG_LEVELS:
        raise ConfigError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")

    log_file_value = values.get("LOG_FILE", DEFAULT_LOG_FILE).strip()
    if not log_file_value:
        raise ConfigError("LOG_FILE is required")
    log_file = Path(log_file_value)

    return Config(
        api_key=_required(values, "API_TENNIS_API_KEY"),
        api_base_url=_api_url(values),
        email_to=_email(values, "EMAIL_TO"),
        email_from=_email(values, "EMAIL_FROM"),
        smtp_host=_required(values, "SMTP_HOST"),
        smtp_port=_integer(values, "SMTP_PORT", 587, minimum=1, maximum=65535),
        smtp_username=_required(values, "SMTP_USERNAME"),
        smtp_password=_required(values, "SMTP_PASSWORD"),
        smtp_use_tls=_boolean(values, "SMTP_USE_TLS", True),
        timezone=_timezone(values),
        lookahead_days=_integer(values, "LOOKAHEAD_DAYS", 7, minimum=0),
        api_timeout_seconds=_integer(values, "API_TIMEOUT_SECONDS", 30, minimum=1),
        log_level=log_level,
        log_file=log_file,
    )


def fetch_matches(
    config: Config,
    *,
    now: datetime | None = None,
    logger: logging.Logger | None = None,
) -> list[Mapping[str, object]]:
    """Fetch the configured date window of ATP Singles fixtures.

    The optional now value is injectable so callers and tests can make the date
    window deterministic. The API response is returned unchanged for filtering
    by a later stage.
    """

    logger = logger or logging.getLogger(LOGGER_NAME)
    timezone = ZoneInfo(config.timezone)
    current = datetime.now(timezone) if now is None else now
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone)
    else:
        current = current.astimezone(timezone)

    date_start = current.date()
    date_stop = date_start + timedelta(days=config.lookahead_days)
    params = {
        "method": "get_fixtures",
        "APIkey": config.api_key,
        "date_start": date_start.isoformat(),
        "date_stop": date_stop.isoformat(),
        "event_type_key": 265,
        "timezone": config.timezone,
    }
    logger.info(
        "requesting ATP fixtures from %s through %s (%s)",
        params["date_start"],
        params["date_stop"],
        config.timezone,
    )

    try:
        response = requests.get(
            config.api_base_url,
            params=params,
            timeout=config.api_timeout_seconds,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        logger.error(
            "API request failed: request timed out after %s seconds",
            config.api_timeout_seconds,
        )
        raise APIError("API request timed out") from exc
    except requests.RequestException as exc:
        status_code = getattr(
            getattr(exc, "response", None), "status_code", "unknown"
        )
        logger.error("API request failed: HTTP status %s", status_code)
        raise APIError("API request failed") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("API response malformed: invalid JSON")
        raise APIError("API response was not valid JSON") from exc

    if not isinstance(payload, Mapping):
        logger.error("API response malformed: expected a JSON object")
        raise APIError("API response was not a JSON object")

    if payload.get("success") not in {1, True, "1", "true"}:
        logger.error("API response unsuccessful")
        raise APIError("API response was unsuccessful")

    result = payload.get("result")
    if not isinstance(result, list):
        logger.error("API response malformed: result is not a list")
        raise APIError("API response result was not a list")

    fixtures = cast(list[Mapping[str, object]], result)
    logger.info("received %s ATP fixture records", len(fixtures))
    return fixtures


def setup_logging(config: Config) -> logging.Logger:
    """Configure stderr and persistent file logging for the script."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, config.log_level))
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    try:
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    except OSError as exc:
        logger.error("logging setup failed: cannot open LOG_FILE")
        raise ConfigError("LOG_FILE cannot be opened") from exc

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def main() -> int:
    """Validate configuration and initialize logging.

    Fetching and email delivery are added by later implementation tasks.
    """

    try:
        config = load_config()
        logger = setup_logging(config)
        logger.info("script started")
        logger.info("configuration loaded; API and email stages are not implemented yet")
        return 0
    except ConfigError as exc:
        print(f"ERROR configuration: {exc}", file=sys.stderr)
        return 1
    except Exception:
        logging.getLogger(LOGGER_NAME).exception("unexpected startup failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
