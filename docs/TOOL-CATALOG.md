# Windows MCP Server — Tool Catalog

All tools run predefined, read-only PowerShell over SSH against a host in
`MCP_ALLOWED_HOSTS`, write an audit record, and return the standard response
object described in [ARCHITECTURE.md](ARCHITECTURE.md#4-response-format).

Common rejections, which happen before any remote execution:
- `"Host not permitted"` — `hostname` is not in `MCP_ALLOWED_HOSTS`.
- `"Invalid service name"` — `get_windows_service` only; the name contains
  characters other than letters, digits, `_ . - $`.
- `"Service not permitted"` — `get_windows_service` only; the name is not in
  `MCP_ALLOWED_SERVICES` (never returned when it is `ALL`).

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
Runs `Get-Service -Name $name`, with the name passed to the remote side as
data (base64), never as script text. `service_name` is the service name
(e.g. `Spooler`), not the display name.

- If `MCP_ALLOWED_SERVICES` lists names, `service_name` must match one exactly
  (case-sensitive).
- If `MCP_ALLOWED_SERVICES=ALL`, any name made of letters, digits and
  `_ . - $` is accepted.
- If the service does not exist on the target, the result is
  `"success": false, "error": "Service not found"` (remote exit code 2).

The tool description sent to clients reflects the configuration (the list of
services, or that any name is accepted), so changing it requires a server
restart.

## Output format notes

These come from Windows PowerShell 5.1's `ConvertTo-Json` and are passed
through unchanged:
- Enum values are numbers, e.g. service `Status` `4` = Running, `1` = Stopped.
- `DateTime` values such as `LastBootUpTime` may be returned as
  `"/Date(<ms since epoch>)/"` strings.

## Planned

See [ROADMAP.md](ROADMAP.md). No planned tool is implemented until it
appears in the table above.
