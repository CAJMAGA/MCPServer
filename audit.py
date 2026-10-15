"""
Audit logging for remote administrative actions.

Each tool invocation produces one JSON object per line in the audit log.
Audit records are written to a file, never to stdout, which is reserved
for the MCP stdio transport.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

AUDIT_LOGGER_NAME = "windows_mcp.audit"
MAX_ERROR_LENGTH = 1000

_logger = logging.getLogger(AUDIT_LOGGER_NAME)
_logger.setLevel(logging.INFO)
_logger.propagate = False


def configure_audit_log(path: Path) -> None:
    """
    Direct audit records to the given file, creating its directory.

    Raises OSError if the file cannot be opened, so the server can refuse
    to start rather than run without an audit trail.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    for old in list(_logger.handlers):
        _logger.removeHandler(old)
        old.close()
    _logger.addHandler(handler)


def new_request_id() -> str:
    return uuid.uuid4().hex


def record(
    *,
    request_id: str,
    tool: str,
    operation: str,
    requested_target: str,
    validated_target: Optional[str],
    success: bool,
    error: Optional[str] = None,
    parameters: Optional[Mapping[str, Any]] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """Write one audit record."""
    if error is not None and len(error) > MAX_ERROR_LENGTH:
        error = error[:MAX_ERROR_LENGTH] + "...[truncated]"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "tool": tool,
        "operation": operation,
        "requested_target": requested_target,
        "validated_target": validated_target,
        "parameters": dict(parameters or {}),
        "success": success,
        "error": error,
        "duration_ms": duration_ms,
    }
    _logger.info(json.dumps(entry, default=str))
