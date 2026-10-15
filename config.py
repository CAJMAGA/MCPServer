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
from typing import Mapping, Optional, Tuple

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# Resolved relative to this file, not the working directory, because MCP
# clients often launch the server from an unrelated directory.
PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
DEFAULT_AUDIT_LOG_FILE = PROJECT_DIR / "logs" / "audit.jsonl"

# SSH host or ~/.ssh/config alias. Must not start with "-" so it can never
# be interpreted as an ssh option, and must not contain whitespace.
_HOST_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$")

# Windows service name, applied both to allowlist entries and to every
# service name a client requests. Excludes quotes, whitespace and the
# Get-Service wildcard characters (* ? [ ]). "$" is allowed for names such
# as MSSQL$INSTANCE.
SERVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.$-]{1,256}$")

# MCP_ALLOWED_SERVICES value that permits querying any valid service name.
ALL_SERVICES = "ALL"

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
    allowed_services: frozenset = frozenset()
    allow_all_services: bool = False
    audit_log_file: Path = DEFAULT_AUDIT_LOG_FILE


def _parse_list(
    name: str, raw: Optional[str], pattern: "re.Pattern[str]", kind: str
) -> frozenset:
    if raw is None or not raw.strip():
        return frozenset()
    items = set()
    for entry in raw.split(","):
        item = entry.strip()
        if not item:
            continue
        if not pattern.match(item):
            raise ConfigError(f"{name} contains an invalid {kind}: {item!r}")
        items.add(item)
    return frozenset(items)


def _parse_services(raw: Optional[str]) -> Tuple[frozenset, bool]:
    """Return (allowed service names, allow_all flag)."""
    entries = [e.strip() for e in (raw or "").split(",") if e.strip()]
    if any(e.upper() == ALL_SERVICES for e in entries):
        if len(entries) > 1:
            raise ConfigError(
                f"MCP_ALLOWED_SERVICES={ALL_SERVICES} must not be combined "
                "with specific service names"
            )
        return frozenset(), True
    services = _parse_list(
        "MCP_ALLOWED_SERVICES", raw, SERVICE_NAME_PATTERN, "service name"
    )
    return services, False


def _parse_path(raw: Optional[str], default: Path) -> Path:
    if raw is None or not raw.strip():
        return default
    path = Path(raw.strip()).expanduser()
    # Relative paths are anchored to the project, not the working directory.
    return path if path.is_absolute() else PROJECT_DIR / path


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
    allowed_services, allow_all_services = _parse_services(
        values.get("MCP_ALLOWED_SERVICES")
    )
    settings = Settings(
        allowed_hosts=_parse_list(
            "MCP_ALLOWED_HOSTS",
            values.get("MCP_ALLOWED_HOSTS"),
            _HOST_PATTERN,
            "host",
        ),
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
        allowed_services=allowed_services,
        allow_all_services=allow_all_services,
        audit_log_file=_parse_path(
            values.get("MCP_AUDIT_LOG_FILE"), DEFAULT_AUDIT_LOG_FILE
        ),
    )
    if not settings.allowed_hosts:
        logger.warning(
            "MCP_ALLOWED_HOSTS is empty; all remote targets will be rejected"
        )
    if not settings.allowed_services and not settings.allow_all_services:
        logger.warning(
            "MCP_ALLOWED_SERVICES is empty; all service queries will be "
            "rejected"
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
