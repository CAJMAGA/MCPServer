import pytest

from config import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SSH_CONNECT_TIMEOUT,
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
