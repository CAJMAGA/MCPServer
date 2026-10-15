import asyncio
import subprocess

import pytest

import server
from config import Settings


@pytest.fixture
def lab_settings(monkeypatch):
    settings = Settings(
        allowed_hosts=frozenset({"windows-lab"}),
        ssh_connect_timeout=7,
        command_timeout=42,
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


def test_rejects_host_not_in_allowlist(lab_settings, fake_run):
    result = server.run_powershell("prod-server", "Get-Date")
    assert result == {
        "success": False,
        "hostname": "prod-server",
        "error": "Host not permitted",
    }
    assert fake_run == []


def test_empty_allowlist_rejects_everything(monkeypatch, fake_run):
    monkeypatch.setattr(
        server,
        "settings",
        Settings(frozenset(), ssh_connect_timeout=5, command_timeout=30),
    )
    result = server.run_powershell("windows-lab", "Get-Date")
    assert result["success"] is False
    assert fake_run == []


def test_uses_configured_timeouts(lab_settings, fake_run):
    result = server.run_powershell("windows-lab", "Get-Date")
    assert result == {
        "success": True,
        "hostname": "windows-lab",
        "data": {"CSName": "LAB01"},
    }
    command, kwargs = fake_run[0]
    assert "ConnectTimeout=7" in command
    assert kwargs["timeout"] == 42
    # Hostname must follow "--" so it can never be parsed as an ssh option.
    assert command[command.index("--") + 1] == "windows-lab"


def test_reports_timeout(lab_settings, monkeypatch):
    def _timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(server.subprocess, "run", _timeout)
    result = server.run_powershell("windows-lab", "Get-Date")
    assert result["success"] is False
    assert result["error"] == "SSH command timed out"


def test_service_tool_rejects_unlisted_service(lab_settings, fake_run):
    result = server.get_windows_service("windows-lab", "BITS")
    assert result["success"] is False
    assert fake_run == []


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
    assert "service_name" in by_name["get_windows_service"].input_schema[
        "required"
    ]
