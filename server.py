from mcp.server.mcpserver import MCPServer
import subprocess
import json
import base64
import sys
import time
from typing import Any, Mapping, Optional
import audit
from config import ConfigError, load_settings

# Load configuration (approved hosts, services, timeouts, audit log) from
# .env / environment. Errors go to stderr; stdout is reserved for the MCP
# stdio transport.
try:
   settings = load_settings()
except ConfigError as e:
   sys.exit(f"Configuration error: {e}")

# Refuse to start without a writable audit log.
try:
   audit.configure_audit_log(settings.audit_log_file)
except OSError as e:
   sys.exit(f"Cannot open audit log {settings.audit_log_file}: {e}")

# Initialize the MCP server
mcp = MCPServer("Windows Infrastructure Lab")

def _execute_ssh(hostname: str, script: str) -> dict:
   """
   Run a PowerShell script on an already-validated host over SSH
   using key authentication.
   """
   # PowerShell EncodedCommand requires UTF-16LE
   encoded = base64.b64encode(
       script.encode("utf-16le")
   ).decode("ascii")
   command = [
       "ssh",
       "-o", "BatchMode=yes",
       "-o", "IdentitiesOnly=yes",
       "-o", f"ConnectTimeout={settings.ssh_connect_timeout}",
       "--",
       hostname,
       "powershell.exe",
       "-NoProfile",
       "-NonInteractive",
       "-EncodedCommand",
       encoded
   ]
   try:
       result = subprocess.run(
           command,
           capture_output=True,
           text=True,
           timeout=settings.command_timeout
       )
       if result.returncode != 0:
           return {
               "success": False,
               "hostname": hostname,
               "error": result.stderr.strip()
                   or result.stdout.strip(),
               "exit_code": result.returncode
           }
       try:
           return {
               "success": True,
               "hostname": hostname,
               "data": json.loads(result.stdout)
           }
       except json.JSONDecodeError:
           return {
               "success": True,
               "hostname": hostname,
               "data": result.stdout.strip()
           }
   except subprocess.TimeoutExpired:
       return {
           "success": False,
           "hostname": hostname,
           "error": "SSH command timed out"
       }
   except Exception as e:
       return {
           "success": False,
           "hostname": hostname,
           "error": str(e)
       }

def _audited(
   result: dict,
   *,
   request_id: str,
   started: float,
   tool: str,
   operation: str,
   hostname: str,
   validated_target: Optional[str],
   parameters: Optional[Mapping[str, Any]],
) -> dict:
   """Write the audit record for a tool call and tag the result."""
   audit.record(
       request_id=request_id,
       tool=tool,
       operation=operation,
       requested_target=hostname,
       validated_target=validated_target,
       success=result["success"],
       error=result.get("error"),
       parameters=parameters,
       duration_ms=int((time.monotonic() - started) * 1000),
   )
   result["request_id"] = request_id
   return result

def run_powershell(
   hostname: str,
   script: str,
   *,
   tool: str,
   operation: str,
   parameters: Optional[Mapping[str, Any]] = None,
) -> dict:
   """
   Execute a predefined PowerShell query on an approved Windows host
   through SSH key authentication, and audit the outcome.
   """
   request_id = audit.new_request_id()
   started = time.monotonic()
   if hostname not in settings.allowed_hosts:
       result = {
           "success": False,
           "hostname": hostname,
           "error": "Host not permitted"
       }
       validated_target = None
   else:
       result = _execute_ssh(hostname, script)
       validated_target = hostname
   return _audited(
       result,
       request_id=request_id,
       started=started,
       tool=tool,
       operation=operation,
       hostname=hostname,
       validated_target=validated_target,
       parameters=parameters,
   )

def reject_request(
   hostname: str,
   error: str,
   *,
   tool: str,
   operation: str,
   parameters: Optional[Mapping[str, Any]] = None,
) -> dict:
   """Reject a request before any remote execution, and audit it."""
   return _audited(
       {"success": False, "hostname": hostname, "error": error},
       request_id=audit.new_request_id(),
       started=time.monotonic(),
       tool=tool,
       operation=operation,
       hostname=hostname,
       validated_target=None,
       parameters=parameters,
   )

@mcp.tool()
def get_windows_system_info(hostname: str) -> dict:
   """
   Retrieve Windows OS, hostname, version, and uptime.

   Args:
       hostname: Approved SSH host or ~/.ssh/config alias
           of the Windows machine.
   """
   script = """
   Get-CimInstance Win32_OperatingSystem |
   Select-Object CSName, Caption, Version,
       LastBootUpTime |
   ConvertTo-Json -Compress
   """
   return run_powershell(
       hostname, script,
       tool="get_windows_system_info",
       operation="read OS information"
   )

@mcp.tool()
def get_windows_cpu(hostname: str) -> dict:
   """
   Retrieve CPU model, core count, and CPU utilization.

   Args:
       hostname: Approved SSH host or ~/.ssh/config alias
           of the Windows machine.
   """
   script = """
   Get-CimInstance Win32_Processor |
   Select-Object Name, NumberOfCores,
       NumberOfLogicalProcessors, LoadPercentage |
   ConvertTo-Json -Compress
   """
   return run_powershell(
       hostname, script,
       tool="get_windows_cpu",
       operation="read CPU information"
   )

@mcp.tool()
def get_windows_memory(hostname: str) -> dict:
   """
   Retrieve total, used, and available physical memory.

   Args:
       hostname: Approved SSH host or ~/.ssh/config alias
           of the Windows machine.
   """
   script = """
   $os = Get-CimInstance Win32_OperatingSystem
   $total = [math]::Round(
       $os.TotalVisibleMemorySize / 1MB, 2
   )
   $free = [math]::Round(
       $os.FreePhysicalMemory / 1MB, 2
   )
   [PSCustomObject]@{
       TotalGB = $total
       FreeGB = $free
       UsedGB = [math]::Round($total - $free, 2)
       UsedPercent = if ($total -gt 0) {
           [math]::Round(
               (($total - $free) / $total) * 100, 2
           )
       } else { 0 }
   } | ConvertTo-Json -Compress
   """
   return run_powershell(
       hostname, script,
       tool="get_windows_memory",
       operation="read memory usage"
   )

_SERVICE_TOOL_DESCRIPTION = f"""
Retrieve the status of an approved Windows service.
Allowed services: {", ".join(sorted(settings.allowed_services)) or "(none configured)"}

Args:
    hostname: Approved SSH host or ~/.ssh/config alias
        of the Windows machine.
    service_name: Name of the service to query (exact, case-sensitive).
""".strip()

@mcp.tool(description=_SERVICE_TOOL_DESCRIPTION)
def get_windows_service(hostname: str, service_name: str) -> dict:
   tool = "get_windows_service"
   operation = "read service status"
   parameters = {"service_name": service_name}
   # service_name is interpolated into the script below; it is safe only
   # because it must exactly match a configured, pattern-validated entry.
   if service_name not in settings.allowed_services:
       return reject_request(
           hostname, "Service not permitted",
           tool=tool, operation=operation, parameters=parameters
       )
   script = f"""
   Get-Service -Name '{service_name}' |
   Select-Object Name, Status, DisplayName |
   ConvertTo-Json -Compress
   """
   return run_powershell(
       hostname, script,
       tool=tool, operation=operation, parameters=parameters
   )

# Start the MCP server using stdio transport
if __name__ == "__main__":
   mcp.run()
