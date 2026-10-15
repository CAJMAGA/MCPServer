# Windows MCP Server — Architecture

This document describes the system as currently implemented. Planned work is
tracked in [ROADMAP.md](ROADMAP.md); security controls are detailed in
[SECURITY.md](SECURITY.md); tools are listed in [TOOL-CATALOG.md](TOOL-CATALOG.md).

## 1. Overview

```
┌──────────────────────┐   MCP (stdio)   ┌───────────────────────────────┐   OpenSSH (key auth)   ┌──────────────────────┐
│  MCP-compatible      │ ──────────────▶ │  Windows MCP Server (Python)  │ ─────────────────────▶ │  Windows endpoint    │
│  AI client (local)   │ ◀────────────── │                               │ ◀───────────────────── │  powershell.exe      │
└──────────────────────┘  JSON results   │  server.py  — tools           │   stdout / stderr      └──────────────────────┘
                                         │  config.py  — settings        │
                                         │  audit.py   — audit log       │──▶ logs/audit.jsonl
                                         └───────────────────────────────┘
                                                  ▲
                                                  │ .env / environment variables
```

- **AI client** — any locally hosted application that speaks MCP. It launches
  the server as a subprocess and communicates over stdio. The server has no
  dependency on a particular client or model.
- **MCP server** — exposes a fixed set of tools, validates every request
  against configured allowlists, runs predefined PowerShell over SSH, writes
  an audit record, and returns structured JSON.
- **Windows endpoints** — machines running the OpenSSH server, reachable by
  an SSH host name or `~/.ssh/config` alias, accepting key-based logins.

## 2. Components

| Module | Responsibility |
|---|---|
| `server.py` | MCP server instance, tool registration, the remote execution helper (`run_powershell` / `_execute_ssh`) and request rejection (`reject_request`). |
| `config.py` | Loads and validates settings from `.env` and the process environment into an immutable `Settings` object. |
| `audit.py` | Writes one JSON audit record per tool call to the audit log file. |
| `tests/` | Unit tests for configuration, authorization, auditing and tool registration. Remote execution is mocked. |

Remote execution, authorization and the tools still live together in
`server.py`. Splitting execution into its own module is a candidate once more
tools exist (see ROADMAP).

## 3. Request flow

1. The AI client calls a tool, e.g. `get_windows_service(hostname, service_name)`.
2. Tool-specific validation runs first (for example, `service_name` must be a
   valid service name and permitted by `MCP_ALLOWED_SERVICES`). Failures are
   rejected via `reject_request`.
3. `run_powershell` checks `hostname` against `MCP_ALLOWED_HOSTS`. Unlisted
   hosts are rejected without starting any process.
4. For approved hosts, the predefined script is base64-encoded as UTF-16LE and
   run as:
   `ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=<n> -- <host> powershell.exe -NoProfile -NonInteractive -EncodedCommand <b64>`
   with a process timeout of `MCP_COMMAND_TIMEOUT` seconds.
5. Output is parsed as JSON when possible; otherwise the trimmed text is
   returned. Scripts can signal known conditions with a dedicated exit code,
   which `run_powershell` maps to a stable error message via
   `exit_code_errors` (e.g. exit 2 → `"Service not found"`).
6. An audit record is written and the result is returned with a `request_id`
   that matches the audit record.

## 4. Response format

All tools return a JSON object:

```json
{ "success": true,  "hostname": "windows-lab", "data": { ... },        "request_id": "<hex>" }
{ "success": false, "hostname": "windows-lab", "error": "<message>",   "request_id": "<hex>", "exit_code": 255 }
```

`exit_code` is present only when the remote command ran and exited non-zero.

## 5. Configuration

Settings are read once at startup. Process environment variables override
values in `.env`. The `.env` file is located next to `config.py`, so the server
finds it regardless of the client's working directory. See `.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `MCP_ALLOWED_HOSTS` | empty (deny all) | Comma-separated SSH hosts / aliases that may be targeted. |
| `MCP_ALLOWED_SERVICES` | empty (deny all) | Comma-separated service names `get_windows_service` may query, or `ALL` for any valid service name. |
| `MCP_SSH_CONNECT_TIMEOUT` | `5` | SSH connection timeout, 1–300 seconds. |
| `MCP_COMMAND_TIMEOUT` | `30` | Maximum runtime per remote command, 1–3600 seconds. |
| `MCP_AUDIT_LOG_FILE` | `logs/audit.jsonl` | Audit log path; relative paths resolve from the project directory. |

Invalid values stop the server at startup with a message on stderr. stdout is
never written to outside the MCP transport.

## 6. Runtime and dependencies

- Python 3.10+, as required by `mcp` (development uses a `.venv` with
  Python 3.14; the macOS system `python3` 3.9 is too old).
- `mcp` (2.x, using `mcp.server.mcpserver.MCPServer`) and `python-dotenv`;
  see `requirements.txt`. `pytest` is in `requirements-dev.txt`.
- The OpenSSH client (`ssh`) on the server host, with keys and any host
  aliases configured in the running user's `~/.ssh/config`.
- Windows endpoints need the OpenSSH server with `powershell.exe` available.

Run tests with `.venv/bin/python -m pytest`.
