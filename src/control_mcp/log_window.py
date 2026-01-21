"""Persistent log window for MCP server activity."""

import threading
import queue
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from typing import Optional


class LogWindow:
    """A persistent popup window that displays MCP server activity logs."""

    _instance: Optional["LogWindow"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the log window (runs in separate thread)."""
        self._message_queue: queue.Queue = queue.Queue()
        self._window_thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._text_widget: Optional[scrolledtext.ScrolledText] = None
        self._running = False

    @classmethod
    def get_instance(cls) -> "LogWindow":
        """Get or create the singleton LogWindow instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = LogWindow()
            return cls._instance

    def start(self) -> None:
        """Start the log window in a separate thread."""
        if self._running:
            return

        self._running = True
        self._window_thread = threading.Thread(target=self._run_window, daemon=True)
        self._window_thread.start()

    def stop(self) -> None:
        """Stop the log window."""
        self._running = False
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Add a message to the log window.

        Args:
            message: The message to log
            level: Log level (INFO, WARN, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        self._message_queue.put(formatted_message)

    def _run_window(self) -> None:
        """Run the tkinter window (called in separate thread)."""
        try:
            self._root = tk.Tk()
            self._root.title("Control MCP - Activity Log")
            self._root.geometry("700x400")
            self._root.configure(bg="#1e1e1e")

            # Make window stay on top
            self._root.attributes("-topmost", True)

            # Create main frame
            main_frame = tk.Frame(self._root, bg="#1e1e1e")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Title label
            title_label = tk.Label(
                main_frame,
                text="MCP Server Activity Log",
                font=("Helvetica", 14, "bold"),
                fg="#ffffff",
                bg="#1e1e1e",
            )
            title_label.pack(pady=(0, 10))

            # Scrolled text widget for logs
            self._text_widget = scrolledtext.ScrolledText(
                main_frame,
                wrap=tk.WORD,
                font=("Monaco", 11),
                bg="#2d2d2d",
                fg="#ffffff",
                insertbackground="#ffffff",
                selectbackground="#404040",
                state=tk.DISABLED,
                height=18,
            )
            self._text_widget.pack(fill=tk.BOTH, expand=True)

            # Configure text tags for different log levels
            self._text_widget.tag_configure("INFO", foreground="#4fc3f7")
            self._text_widget.tag_configure("WARN", foreground="#ffb74d")
            self._text_widget.tag_configure("ERROR", foreground="#ef5350")
            self._text_widget.tag_configure("DEBUG", foreground="#81c784")
            self._text_widget.tag_configure("TOOL", foreground="#ce93d8")

            # Button frame
            button_frame = tk.Frame(main_frame, bg="#1e1e1e")
            button_frame.pack(fill=tk.X, pady=(10, 0))

            # Clear button
            clear_button = tk.Button(
                button_frame,
                text="Clear Log",
                command=self._clear_log,
                font=("Helvetica", 11),
                bg="#404040",
                fg="#ffffff",
                activebackground="#505050",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                padx=15,
                pady=5,
            )
            clear_button.pack(side=tk.LEFT)

            # Toggle always on top button
            self._topmost_var = tk.BooleanVar(value=True)
            topmost_button = tk.Checkbutton(
                button_frame,
                text="Always on Top",
                variable=self._topmost_var,
                command=self._toggle_topmost,
                font=("Helvetica", 11),
                bg="#1e1e1e",
                fg="#ffffff",
                activebackground="#1e1e1e",
                activeforeground="#ffffff",
                selectcolor="#404040",
            )
            topmost_button.pack(side=tk.LEFT, padx=(20, 0))

            # Close button
            close_button = tk.Button(
                button_frame,
                text="Close",
                command=self._on_close,
                font=("Helvetica", 11),
                bg="#c62828",
                fg="#ffffff",
                activebackground="#d32f2f",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                padx=15,
                pady=5,
            )
            close_button.pack(side=tk.RIGHT)

            # Handle window close button (X)
            self._root.protocol("WM_DELETE_WINDOW", self._on_close)

            # Add initial message
            self._append_message("[Server] Log window started - monitoring MCP activity", "INFO")

            # Start processing message queue
            self._process_queue()

            # Run the main loop
            self._root.mainloop()

        except Exception as e:
            print(f"Log window error: {e}")
        finally:
            self._running = False

    def _process_queue(self) -> None:
        """Process messages from the queue and display them."""
        if not self._running or not self._root:
            return

        try:
            while True:
                message = self._message_queue.get_nowait()
                self._append_message(message)
        except queue.Empty:
            pass

        # Schedule next queue check
        if self._running and self._root:
            self._root.after(100, self._process_queue)

    def _append_message(self, message: str, level: str = None) -> None:
        """Append a message to the text widget."""
        if not self._text_widget:
            return

        # Determine tag from message or explicit level
        tag = level
        if tag is None:
            if "[INFO]" in message:
                tag = "INFO"
            elif "[WARN]" in message:
                tag = "WARN"
            elif "[ERROR]" in message:
                tag = "ERROR"
            elif "[DEBUG]" in message:
                tag = "DEBUG"
            elif "[TOOL]" in message:
                tag = "TOOL"
            else:
                tag = "INFO"

        self._text_widget.configure(state=tk.NORMAL)
        self._text_widget.insert(tk.END, message + "\n", tag)
        self._text_widget.see(tk.END)  # Auto-scroll to bottom
        self._text_widget.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        """Clear all log messages."""
        if self._text_widget:
            self._text_widget.configure(state=tk.NORMAL)
            self._text_widget.delete(1.0, tk.END)
            self._text_widget.configure(state=tk.DISABLED)
            self._append_message("[Server] Log cleared", "INFO")

    def _toggle_topmost(self) -> None:
        """Toggle the always-on-top setting."""
        if self._root:
            self._root.attributes("-topmost", self._topmost_var.get())

    def _on_close(self) -> None:
        """Handle window close."""
        self._running = False
        if self._root:
            self._root.destroy()
            self._root = None


# Convenience function for logging
def log(message: str, level: str = "INFO") -> None:
    """
    Log a message to the log window.

    Args:
        message: The message to log
        level: Log level (INFO, WARN, ERROR, DEBUG, TOOL)
    """
    try:
        window = LogWindow.get_instance()
        window.log(message, level)
    except Exception:
        pass  # Silently ignore if window not available


def start_log_window() -> LogWindow:
    """Start the log window and return the instance."""
    window = LogWindow.get_instance()
    window.start()
    return window
