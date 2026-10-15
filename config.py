"""
Configuration loading and validation for the Windows MCP server.

Settings come from the process environment, falling back to a .env file
located next to this module. Real environment variables take precedence
over values in .env.
"""
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# Resolved relative to this file, not the working directory, because MCP
# clients often launch the server from an unrelated directory.
ENV_FILE = Path(__file__).resolve().parent / ".env"

# SSH host or ~/.ssh/config alias. Must not start with "-" so it can never
# be interpreted as an ssh option, and must not contain whitespace.
_HOST_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$")

DEFAULT_SSH_CONNECT_TIMEOUT = 5
DEFAULT_COMMAND_TIMEOUT = 30
MAX_SSH_CONNECT_TIMEOUT = 300
MAX_COMMAND_TIMEOUT = 3600


class ConfigError(ValueError):
    """Raised when configuration values are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    allowed_hosts: frozenset
    ssh_connect_timeout: int
    command_timeout: int


def _parse_hosts(raw: Optional[str]) -> frozenset:
    if raw is None or not raw.strip():
        return frozenset()
    hosts = set()
    for entry in raw.split(","):
        host = entry.strip()
        if not host:
            continue
        if not _HOST_PATTERN.match(host):
            raise ConfigError(
                f"MCP_ALLOWED_HOSTS contains an invalid host: {host!r}"
            )
        hosts.add(host)
    return frozenset(hosts)


def _parse_timeout(
    name: str, raw: Optional[str], default: int, maximum: int
) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from None
    if not 1 <= value <= maximum:
        raise ConfigError(
            f"{name} must be between 1 and {maximum} seconds, got {value}"
        )
    return value


def settings_from_mapping(values: Mapping[str, str]) -> Settings:
    """Build validated Settings from a mapping of variable names to values."""
    settings = Settings(
        allowed_hosts=_parse_hosts(values.get("MCP_ALLOWED_HOSTS")),
        ssh_connect_timeout=_parse_timeout(
            "MCP_SSH_CONNECT_TIMEOUT",
            values.get("MCP_SSH_CONNECT_TIMEOUT"),
            DEFAULT_SSH_CONNECT_TIMEOUT,
            MAX_SSH_CONNECT_TIMEOUT,
        ),
        command_timeout=_parse_timeout(
            "MCP_COMMAND_TIMEOUT",
            values.get("MCP_COMMAND_TIMEOUT"),
            DEFAULT_COMMAND_TIMEOUT,
            MAX_COMMAND_TIMEOUT,
        ),
    )
    if not settings.allowed_hosts:
        logger.warning(
            "MCP_ALLOWED_HOSTS is empty; all remote targets will be rejected"
        )
    return settings


def load_settings(
    env_file: Optional[Path] = ENV_FILE,
    environ: Optional[Mapping[str, str]] = None,
) -> Settings:
    """
    Load settings from the .env file and the process environment.

    Process environment values override .env values. os.environ is not
    modified.
    """
    values = {}
    if env_file is not None and env_file.is_file():
        values.update(
            {k: v for k, v in dotenv_values(env_file).items() if v is not None}
        )
    values.update(os.environ if environ is None else environ)
    return settings_from_mapping(values)
