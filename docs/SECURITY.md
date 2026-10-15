# Windows MCP Server — Security

Security controls are enforced by the server itself and do not depend on the
AI client behaving correctly. This document separates what is **implemented**
from what is **not implemented**.

## 1. Trust boundaries

- **AI client → MCP server.** All tool arguments are treated as untrusted.
- **MCP server → Windows endpoint.** Connections use OpenSSH with key-based
  authentication as the user running the server.
- **Configuration.** `.env`, the process environment and the running user's
  `~/.ssh/config` are trusted. Anyone who can edit them controls which
  machines the server can reach.

## 2. Implemented controls

### Target authorization
- Only hosts listed in `MCP_ALLOWED_HOSTS` can be targeted; everything else is
  rejected with `"Host not permitted"` before any process starts.
- Missing or empty allowlist means **no** host is permitted.
- Each allowlist entry must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$`, so it
  cannot start with `-` or contain whitespace, `@` or shell characters.
  Invalid entries stop the server at startup.
- The hostname is passed to `ssh` after `--`, so it can never be read as an
  ssh option.
- A rejected target is never replaced with another one.

### Remote execution
- No arbitrary command execution. Every tool runs a fixed, predefined
  PowerShell script.
- Scripts are sent with `-EncodedCommand` (base64 UTF-16LE) and passed to
  `subprocess.run` as an argument list — no local shell is involved.
- The only user-supplied value placed inside a script is `service_name`, and
  only after it exactly matches an entry in `MCP_ALLOWED_SERVICES`. Allowlist
  entries must match `^[A-Za-z0-9_.$-]{1,256}$`, which excludes quotes,
  whitespace and wildcard characters. `$` is literal inside the single-quoted
  PowerShell string.
- `ssh` runs with `BatchMode=yes` (never prompts) and `IdentitiesOnly=yes`.
- Connection and command timeouts are enforced (`MCP_SSH_CONNECT_TIMEOUT`,
  `MCP_COMMAND_TIMEOUT`).
- All current tools are read-only.

### Credentials
- No passwords, tokens or keys are stored in code or `.env`. Authentication
  uses SSH keys managed outside the project.
- `.env`, logs and common private key file names are listed in `.gitignore`.
  Only `.env.example` is committed.

### Auditing
- Every tool call, including rejected ones, writes one JSON line to
  `MCP_AUDIT_LOG_FILE` (default `logs/audit.jsonl`) with: `timestamp` (UTC),
  `request_id`, `tool`, `operation`, `requested_target`, `validated_target`
  (null if rejected), `parameters`, `success`, `error`, `duration_ms`.
- The same `request_id` is returned to the client so a response can be
  matched to its audit record.
- Scripts and command output are not logged. Error text is truncated to
  1000 characters.
- If the audit log cannot be opened at startup, the server refuses to start.

## 3. Not implemented / known limitations

- **No validation of resolved addresses.** Authorization is by SSH host name
  or alias only. Where an alias actually connects is decided by
  `~/.ssh/config` and DNS, which are therefore part of the trust boundary.
  The owner decided on 2026-10-14 not to add a network-range check. This
  differs from the "validate resolved addresses" guidance in `CLAUDE.md`.
- **No per-tool or per-user authorization.** Any client that can launch the
  server can call every tool against every allowed host.
- **No approval workflow** for high-impact operations. None exist yet; one
  will be needed before tools that change system state are added.
- **Audit write failures at runtime** (for example, a full disk after startup)
  are reported on stderr by Python logging but do not block the operation.
- **Audit logs are not tamper-protected** and have no rotation.
- **Least privilege** depends on the Windows account the SSH key logs into;
  the server does not enforce it.
- SSH error text from the endpoint is returned to the client and recorded in
  the audit log as-is (truncated).

## 4. Guidance for new tools

- Use fixed scripts. Never build PowerShell from client input except through
  a validated allowlist, and keep values inside single-quoted strings.
- Route all remote calls through `run_powershell` and all early rejections
  through `reject_request` so they are authorized and audited the same way.
- Keep tools that change system state separate from read-only tools, and do
  not add them without an approval mechanism.
- Never run destructive operations in tests. Mock `subprocess.run`.
