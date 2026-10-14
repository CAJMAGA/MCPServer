from mcp.server.mcpserver import MCPServer
import subprocess
import json
import base64
# Initialize the MCP server
mcp = MCPServer("Windows Infrastructure Lab")
# Approved SSH hosts / aliases configured in ~/.ssh/config
ALLOWED_HOSTS = {
   "windows-lab"
}

def run_powershell(hostname: str, script: str) -> dict:
   """
   Execute a predefined PowerShell query on Windows
   through SSH key authentication.
   """
   if hostname not in ALLOWED_HOSTS:
       return {
           "success": False,
           "hostname": hostname,
           "error": "Host not permitted"
       }
   # PowerShell EncodedCommand requires UTF-16LE
   encoded = base64.b64encode(
       script.encode("utf-16le")
   ).decode("ascii")
   command = [
       "ssh",
       "-o", "BatchMode=yes",
       "-o", "IdentitiesOnly=yes",
       "-o", "ConnectTimeout=5",
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
           timeout=30
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
   return run_powershell(hostname, script)

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
   return run_powershell(hostname, script)

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
   return run_powershell(hostname, script)

@mcp.tool()
def get_windows_service(hostname: str, service_name: str) -> dict:
   """
   Retrieve the status of an approved Windows service.
   Allowed services:
   Spooler, WinRM, W32Time, EventLog

   Args:
       hostname: Approved SSH host or ~/.ssh/config alias
           of the Windows machine.
       service_name: Name of the service to query.
   """
   allowed_services = {
       "Spooler",
       "WinRM",
       "W32Time",
       "EventLog"
   }
   if service_name not in allowed_services:
       return {
           "success": False,
           "error": "Service not permitted"
       }
   script = f"""
   Get-Service -Name '{service_name}' |
   Select-Object Name, Status, DisplayName |
   ConvertTo-Json -Compress
   """
   return run_powershell(hostname, script)

# Start the MCP server using stdio transport
if __name__ == "__main__":
   mcp.run()