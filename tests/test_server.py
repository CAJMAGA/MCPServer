import asyncio
import json
import subprocess

import pytest

import audit
import server
from config import Settings


@pytest.fixture
def lab_settings(monkeypatch):
    settings = Settings(
        allowed_hosts=frozenset({"windows-lab"}),
        ssh_connect_timeout=7,
        command_timeout=42,
        allowed_services=frozenset({"Spooler", "MSSQL$SQLEXPRESS"}),
    )
    monkeypatch.setattr(server, "settings", settings)
    return settings


@pytest.fixture
def fake_run(monkeypatch):
    """Replace subprocess.run so no real SSH connection is ever made."""
    calls = []

    def _run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 0, stdout='{"CSName": "LAB01"}', stderr=""
        )

    monkeypatch.setattr(server.subprocess, "run", _run)
    return calls


@pytest.fixture
def audit_log(tmp_path):
    """Send audit records to a temporary file and return a reader."""
    path = tmp_path / "audit.jsonl"
    audit.configure_audit_log(path)

    def _read():
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    return _read


def _run(hostname, script="Get-Date"):
    return server.run_powershell(
        hostname, script, tool="test_tool", operation="test operation"
    )


def test_rejects_host_not_in_allowlist(lab_settings, fake_run, audit_log):
    result = _run("prod-server")
    assert result["success"] is False
    assert result["hostname"] == "prod-server"
    assert result["error"] == "Host not permitted"
    assert fake_run == []


def test_empty_allowlist_rejects_everything(monkeypatch, fake_run, audit_log):
    monkeypatch.setattr(
        server,
        "settings",
        Settings(frozenset(), ssh_connect_timeout=5, command_timeout=30),
    )
    assert _run("windows-lab")["success"] is False
    assert fake_run == []


def test_uses_configured_timeouts(lab_settings, fake_run, audit_log):
    result = _run("windows-lab")
    assert result["success"] is True
    assert result["data"] == {"CSName": "LAB01"}
    command, kwargs = fake_run[0]
    assert "ConnectTimeout=7" in command
    assert kwargs["timeout"] == 42
    # Hostname must follow "--" so it can never be parsed as an ssh option.
    assert command[command.index("--") + 1] == "windows-lab"


def test_reports_timeout(lab_settings, monkeypatch, audit_log):
    def _timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(server.subprocess, "run", _timeout)
    result = _run("windows-lab")
    assert result["success"] is False
    assert result["error"] == "SSH command timed out"


def test_service_tool_rejects_unlisted_service(
    lab_settings, fake_run, audit_log
):
    result = server.get_windows_service("windows-lab", "BITS")
    assert result["success"] is False
    assert result["error"] == "Service not permitted"
    assert fake_run == []


def test_service_tool_queries_configured_service(
    lab_settings, fake_run, audit_log
):
    result = server.get_windows_service("windows-lab", "MSSQL$SQLEXPRESS")
    assert result["success"] is True
    assert len(fake_run) == 1


def test_service_tool_still_checks_host(lab_settings, fake_run, audit_log):
    result = server.get_windows_service("prod-server", "Spooler")
    assert result["error"] == "Host not permitted"
    assert fake_run == []


def test_successful_call_is_audited(lab_settings, fake_run, audit_log):
    result = _run("windows-lab")
    [entry] = audit_log()
    assert entry["request_id"] == result["request_id"]
    assert entry["tool"] == "test_tool"
    assert entry["operation"] == "test operation"
    assert entry["requested_target"] == "windows-lab"
    assert entry["validated_target"] == "windows-lab"
    assert entry["success"] is True
    assert entry["error"] is None
    assert entry["timestamp"].endswith("+00:00")
    assert isinstance(entry["duration_ms"], int)


def test_rejected_host_is_audited(lab_settings, fake_run, audit_log):
    _run("prod-server")
    [entry] = audit_log()
    assert entry["requested_target"] == "prod-server"
    assert entry["validated_target"] is None
    assert entry["success"] is False
    assert entry["error"] == "Host not permitted"


def test_rejected_service_is_audited(lab_settings, fake_run, audit_log):
    result = server.get_windows_service("windows-lab", "BITS")
    [entry] = audit_log()
    assert entry["request_id"] == result["request_id"]
    assert entry["tool"] == "get_windows_service"
    assert entry["parameters"] == {"service_name": "BITS"}
    assert entry["validated_target"] is None
    assert entry["error"] == "Service not permitted"


def test_failed_execution_is_audited(lab_settings, monkeypatch, audit_log):
    def _fail(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 255, stdout="", stderr="Permission denied (publickey)."
        )

    monkeypatch.setattr(server.subprocess, "run", _fail)
    _run("windows-lab")
    [entry] = audit_log()
    assert entry["validated_target"] == "windows-lab"
    assert entry["success"] is False
    assert entry["error"] == "Permission denied (publickey)."


def test_audit_truncates_long_errors(audit_log):
    audit.record(
        request_id="r",
        tool="t",
        operation="o",
        requested_target="h",
        validated_target=None,
        success=False,
        error="x" * 5000,
    )
    [entry] = audit_log()
    assert len(entry["error"]) < 1100
    assert entry["error"].endswith("[truncated]")


def test_tools_are_registered():
    tools = asyncio.run(server.mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == {
        "get_windows_system_info",
        "get_windows_cpu",
        "get_windows_memory",
        "get_windows_service",
    }
    for tool in tools:
        assert "hostname" in tool.input_schema["required"]
    service_tool = by_name["get_windows_service"]
    assert "service_name" in service_tool.input_schema["required"]
    # Description reflects the configured allowlist (set in conftest.py).
    assert "Spooler, WinRM" in service_tool.description
