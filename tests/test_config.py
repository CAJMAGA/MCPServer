import pytest

from pathlib import Path

from config import (
    DEFAULT_AUDIT_LOG_FILE,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SSH_CONNECT_TIMEOUT,
    PROJECT_DIR,
    ConfigError,
    load_settings,
    settings_from_mapping,
)


def test_parses_comma_separated_hosts():
    settings = settings_from_mapping(
        {"MCP_ALLOWED_HOSTS": " windows-lab , win2.lab ,,windows-lab"}
    )
    assert settings.allowed_hosts == frozenset({"windows-lab", "win2.lab"})


@pytest.mark.parametrize("raw", [None, "", "   ", " , ,"])
def test_missing_or_empty_hosts_denies_all(raw):
    values = {} if raw is None else {"MCP_ALLOWED_HOSTS": raw}
    assert settings_from_mapping(values).allowed_hosts == frozenset()


@pytest.mark.parametrize(
    "host",
    [
        "-oProxyCommand=calc",
        "windows lab",
        "user@windows-lab",
        "host;rm",
        "a" * 254,
    ],
)
def test_rejects_invalid_host_entries(host):
    with pytest.raises(ConfigError):
        settings_from_mapping({"MCP_ALLOWED_HOSTS": f"windows-lab,{host}"})


def test_timeout_defaults():
    settings = settings_from_mapping({})
    assert settings.ssh_connect_timeout == DEFAULT_SSH_CONNECT_TIMEOUT
    assert settings.command_timeout == DEFAULT_COMMAND_TIMEOUT


def test_timeouts_from_values():
    settings = settings_from_mapping(
        {"MCP_SSH_CONNECT_TIMEOUT": "10", "MCP_COMMAND_TIMEOUT": " 120 "}
    )
    assert settings.ssh_connect_timeout == 10
    assert settings.command_timeout == 120


@pytest.mark.parametrize(
    "name", ["MCP_SSH_CONNECT_TIMEOUT", "MCP_COMMAND_TIMEOUT"]
)
@pytest.mark.parametrize("raw", ["abc", "1.5", "0", "-5", "100000"])
def test_rejects_invalid_timeouts(name, raw):
    with pytest.raises(ConfigError):
        settings_from_mapping({name: raw})


def test_loads_values_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MCP_ALLOWED_HOSTS=lab-a,lab-b\nMCP_COMMAND_TIMEOUT=45\n"
    )
    settings = load_settings(env_file=env_file, environ={})
    assert settings.allowed_hosts == frozenset({"lab-a", "lab-b"})
    assert settings.command_timeout == 45


def test_environment_overrides_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("MCP_ALLOWED_HOSTS=from-file\n")
    settings = load_settings(
        env_file=env_file, environ={"MCP_ALLOWED_HOSTS": "from-env"}
    )
    assert settings.allowed_hosts == frozenset({"from-env"})


def test_missing_env_file_is_not_an_error(tmp_path):
    settings = load_settings(env_file=tmp_path / "absent.env", environ={})
    assert settings.allowed_hosts == frozenset()


def test_parses_allowed_services():
    settings = settings_from_mapping(
        {"MCP_ALLOWED_SERVICES": "Spooler, WinRM ,MSSQL$SQLEXPRESS"}
    )
    assert settings.allowed_services == frozenset(
        {"Spooler", "WinRM", "MSSQL$SQLEXPRESS"}
    )


def test_missing_services_denies_all():
    settings = settings_from_mapping({})
    assert settings.allowed_services == frozenset()
    assert settings.allow_all_services is False


@pytest.mark.parametrize("raw", ["ALL", "all", " All ", "ALL,"])
def test_all_services_keyword(raw):
    settings = settings_from_mapping({"MCP_ALLOWED_SERVICES": raw})
    assert settings.allow_all_services is True
    assert settings.allowed_services == frozenset()


def test_specific_services_do_not_allow_all():
    settings = settings_from_mapping({"MCP_ALLOWED_SERVICES": "Spooler"})
    assert settings.allow_all_services is False


@pytest.mark.parametrize("raw", ["ALL,Spooler", "Spooler, all"])
def test_all_cannot_be_combined_with_names(raw):
    with pytest.raises(ConfigError):
        settings_from_mapping({"MCP_ALLOWED_SERVICES": raw})


@pytest.mark.parametrize(
    "service",
    [
        "Spooler'; Stop-Computer; '",
        "Win RM",
        "Win*",
        "Spool?r",
        "[Ss]pooler",
        "a’b",
        "x" * 257,
    ],
)
def test_rejects_unsafe_service_names(service):
    with pytest.raises(ConfigError):
        settings_from_mapping({"MCP_ALLOWED_SERVICES": f"Spooler,{service}"})


def test_audit_log_default():
    assert settings_from_mapping({}).audit_log_file == DEFAULT_AUDIT_LOG_FILE


def test_relative_audit_log_resolves_from_project_dir():
    settings = settings_from_mapping({"MCP_AUDIT_LOG_FILE": "var/a.jsonl"})
    assert settings.audit_log_file == PROJECT_DIR / "var" / "a.jsonl"


def test_absolute_audit_log_path_kept(tmp_path):
    path = tmp_path / "audit.jsonl"
    settings = settings_from_mapping({"MCP_AUDIT_LOG_FILE": str(path)})
    assert settings.audit_log_file == Path(path)
