"""Logging for MCP server activity.

Logs are written to:
1. A file in the logs/ folder (logs/mcp-server-YYYY-MM-DD.log)
2. stderr for Claude's MCP server log viewer

Note: GUI log window is not compatible with MCP servers on macOS because:
- MCP servers use the main thread for asyncio
- tkinter on macOS requires the main thread
- Running tkinter in a background thread causes NSWindow crashes
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO


class MCPLogger:
    """Logger that writes to both a log file and stderr."""

    _instance: Optional["MCPLogger"] = None
    _enabled: bool = True

    def __init__(self):
        """Initialize the logger."""
        self._enabled = True
        self._log_file: Optional[TextIO] = None
        self._log_path: Optional[Path] = None
        self._setup_log_file()

    def _setup_log_file(self) -> None:
        """Set up the log file in the logs directory."""
        try:
            # Find the project root (parent of src directory)
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            logs_dir = project_root / "logs"

            # Create logs directory if it doesn't exist
            logs_dir.mkdir(exist_ok=True)

            # Create log file with today's date
            date_str = datetime.now().strftime("%Y-%m-%d")
            self._log_path = logs_dir / f"mcp-server-{date_str}.log"

            # Open log file in append mode
            self._log_file = open(self._log_path, "a", encoding="utf-8")

            # Write session header
            session_header = f"\n{'='*60}\nMCP Server Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n"
            self._log_file.write(session_header)
            self._log_file.flush()

        except Exception as e:
            # If we can't set up file logging, continue with stderr only
            print(f"[WARN] Could not set up file logging: {e}", file=sys.stderr)
            self._log_file = None

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
        Log a message to both the log file and stderr.

        Args:
            message: The message to log
            level: Log level (INFO, WARN, ERROR, DEBUG, TOOL)
        """
        if not self._enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        formatted_message = f"[{timestamp}] [{level}] {message}"

        # Write to log file
        if self._log_file:
            try:
                self._log_file.write(formatted_message + "\n")
                self._log_file.flush()
            except Exception:
                pass  # Don't let file logging errors crash the server

        # Write to stderr so it appears in Claude's MCP logs
        print(formatted_message, file=sys.stderr)

    def get_log_path(self) -> Optional[str]:
        """Return the path to the current log file."""
        return str(self._log_path) if self._log_path else None

    def close(self) -> None:
        """Close the log file."""
        if self._log_file:
            try:
                self._log_file.write(f"\n{'='*60}\nSession Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n")
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None


# Convenience functions
def log(message: str, level: str = "INFO") -> None:
    """
    Log a message to the log file and stderr.

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
    Logs are written to both the logs/ folder and stderr.
    """
    logger = MCPLogger.get_instance()
    if logger.get_log_path():
        log(f"Logging to: {logger.get_log_path()}", "INFO")
    return logger
