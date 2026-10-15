# Windows MCP Server — Tool Catalog

All tools run predefined, read-only PowerShell over SSH against a host in
`MCP_ALLOWED_HOSTS`, write an audit record, and return the standard response
object described in [ARCHITECTURE.md](ARCHITECTURE.md#4-response-format).

Common rejections, which happen before any remote execution:
- `"Host not permitted"` — `hostname` is not in `MCP_ALLOWED_HOSTS`.
- `"Service not permitted"` — `get_windows_service` only.

## Implemented

| Tool | Parameters | Returns (`data`) | Access |
|---|---|---|---|
| `get_windows_system_info` | `hostname` | `CSName`, `Caption`, `Version`, `LastBootUpTime` | Read-only |
| `get_windows_cpu` | `hostname` | `Name`, `NumberOfCores`, `NumberOfLogicalProcessors`, `LoadPercentage` (object, or a list on multi-socket machines) | Read-only |
| `get_windows_memory` | `hostname` | `TotalGB`, `FreeGB`, `UsedGB`, `UsedPercent` | Read-only |
| `get_windows_service` | `hostname`, `service_name` | `Name`, `Status`, `DisplayName` | Read-only |

### get_windows_system_info
Reads `Win32_OperatingSystem`.

### get_windows_cpu
Reads `Win32_Processor`. `LoadPercentage` is a point-in-time sample.

### get_windows_memory
Calculated from `Win32_OperatingSystem` `TotalVisibleMemorySize` and
`FreePhysicalMemory`, in GB rounded to 2 decimals.

### get_windows_service
Runs `Get-Service -Name '<service_name>'`. `service_name` must exactly
(case-sensitively) match an entry in `MCP_ALLOWED_SERVICES`. The tool
description sent to clients lists the configured services, so changing the
allowlist requires a server restart.

## Output format notes

These come from Windows PowerShell 5.1's `ConvertTo-Json` and are passed
through unchanged:
- Enum values are numbers, e.g. service `Status` `4` = Running, `1` = Stopped.
- `DateTime` values such as `LastBootUpTime` may be returned as
  `"/Date(<ms since epoch>)/"` strings.

## Planned

See [ROADMAP.md](ROADMAP.md). No planned tool is implemented until it
appears in the table above.
