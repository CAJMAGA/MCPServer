# Windows MCP Server — Roadmap

Status of milestones toward the goals in [VISION.md](VISION.md). Only items
marked done are implemented.

## Milestone 1 — Foundation ✅ Done

- [x] MCP server over stdio with the official Python SDK
- [x] Remote PowerShell over OpenSSH with key authentication
- [x] Host allowlist with fail-closed default
- [x] Read-only diagnostic tools: system info, CPU, memory, service status
- [x] Configuration from `.env` / environment with startup validation
- [x] Service allowlist moved to configuration
- [x] Connection and command timeouts
- [x] JSON-lines audit log with request IDs returned to clients
- [x] Unit tests with mocked remote execution
- [x] Core documentation (architecture, security, tool catalog, roadmap)

## Milestone 2 — Hardening and structure

- [ ] Move SSH execution out of `server.py` into its own module as the tool
      count grows
- [ ] Normalize PowerShell output (enum names, ISO 8601 dates)
- [ ] Classify errors (unreachable, auth failure, timeout, remote error) into
      a stable `error_type` field
- [ ] Mark read-only tools with MCP tool annotations
- [ ] Audit log rotation
- [ ] Integration tests against approved lab endpoints (read-only)

## Milestone 3 — Expanded diagnostics (read-only)

- [ ] Disk usage
- [ ] Event log queries (bounded by log name, time window and count)
- [ ] Running processes
- [ ] Network configuration and connectivity checks
- [ ] Installed software and update inventory

## Milestone 4 — Controlled administration

Requires a design for approval and per-tool authorization first.

- [ ] Approval workflow for state-changing operations
- [ ] Separate allowlists / permissions for modifying tools
- [ ] Service start / stop / restart for approved services

## Later

Multi-endpoint operations, Active Directory integration, Windows Update
management, software deployment, policy-based permissions. See VISION.md.

## Decisions

- **2026-10-14:** Remote transport is OpenSSH, not WinRM.
- **2026-10-14:** No network-range (CIDR) check on resolved addresses; host
  authorization is by SSH host name / alias. See SECURITY.md §3.
