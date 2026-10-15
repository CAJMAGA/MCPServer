import os
import tempfile
from pathlib import Path

# Fix configuration before server.py is imported so tests never depend on
# the developer's real .env or write to the real audit log.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="mcp-tests-"))
os.environ["MCP_ALLOWED_HOSTS"] = "windows-lab"
os.environ["MCP_ALLOWED_SERVICES"] = "Spooler,WinRM"
os.environ["MCP_SSH_CONNECT_TIMEOUT"] = "5"
os.environ["MCP_COMMAND_TIMEOUT"] = "30"
os.environ["MCP_AUDIT_LOG_FILE"] = str(_TEST_DIR / "audit.jsonl")
