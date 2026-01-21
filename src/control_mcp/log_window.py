"""Logging for MCP server activity.

Note: GUI log window is not compatible with MCP servers on macOS because:
- MCP servers use the main thread for asyncio
- tkinter on macOS requires the main thread
- Running tkinter in a background thread causes NSWindow crashes

Instead, this module provides stderr-based logging that appears in Claude's
MCP server logs at: ~/Library/Logs/Claude/mcp-server-control-mcp.log
"""

import sys
from datetime import datetime
from typing import Optional


class MCPLogger:
    """Simple logger that writes to stderr for MCP server activity."""

    _instance: Optional["MCPLogger"] = None
    _enabled: bool = True

    def __init__(self):
        """Initialize the logger."""
        self._enabled = True

    @classmethod
    def get_instance(cls) -> "MCPLogger":
        """Get or create the singleton MCPLogger instance."""
        if cls._instance is None:
            cls._instance = MCPLogger()
        return cls._instance

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable logging."""
        self._enabled = enabled

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Log a message to stderr.

        Args:
            message: The message to log
            level: Log level (INFO, WARN, ERROR, DEBUG, TOOL)
        """
        if not self._enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"

        # Write to stderr so it appears in Claude's MCP logs
        print(formatted_message, file=sys.stderr)


# Convenience functions
def log(message: str, level: str = "INFO") -> None:
    """
    Log a message to stderr.

    Args:
        message: The message to log
        level: Log level (INFO, WARN, ERROR, DEBUG, TOOL)
    """
    try:
        logger = MCPLogger.get_instance()
        logger.log(message, level)
    except Exception:
        pass  # Silently ignore if logging fails


def start_log_window() -> MCPLogger:
    """
    Initialize and return the logger.

    Note: This no longer starts a GUI window due to macOS thread restrictions.
    Logs are written to stderr which appears in Claude's MCP logs.
    """
    logger = MCPLogger.get_instance()
    return logger
