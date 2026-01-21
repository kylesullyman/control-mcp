"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .mouse_control import MouseController
from .log_window import start_log_window, log


class MouseControlServer:
    """MCP server that provides mouse control tools."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("control-mcp")
        self.mouse = MouseController()

        # Start the log window
        self.log_window = start_log_window()
        log("MCP Server initialized", "INFO")
        log(f"Screen size: {self.mouse.screen_width}x{self.mouse.screen_height}", "INFO")

        self._setup_handlers()

    def _setup_handlers(self):
        """Set up request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available mouse control tools."""
            return [
                Tool(
                    name="get_cursor_position",
                    description="Get the current mouse cursor position on the user's screen. Use this when the user asks where their mouse is, wants to know cursor coordinates, or before performing click operations to understand current position.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="move_cursor",
                    description="Move the mouse cursor to specific screen coordinates. Use this to navigate to buttons, menus, icons, or any UI element on the user's screen. All movements are smooth and animated over 0.3 seconds by default.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate (pixels from left edge of screen)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (pixels from top edge of screen)",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration of movement in seconds (default: 0.3 for smooth movement)",
                                "default": 0.3,
                            },
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="click",
                    description="Perform mouse click to interact with UI elements like buttons, links, menus, icons, checkboxes, or any clickable element. Supports left/right/middle click, double-click, and clicking at specific coordinates or current cursor position.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate to click at (optional, uses current cursor position if not provided)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to click at (optional, uses current cursor position if not provided)",
                            },
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "description": "Mouse button to click (left for normal click, right for context menu)",
                                "default": "left",
                            },
                            "clicks": {
                                "type": "number",
                                "description": "Number of clicks (use 2 for double-click to open files/apps)",
                                "default": 1,
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between clicks in seconds",
                                "default": 0.1,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="drag",
                    description="Drag from one position to another. Use for moving files, selecting text, resizing windows, drawing, or any drag-and-drop operation on the user's screen.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_x": {
                                "type": "number",
                                "description": "Starting X coordinate",
                            },
                            "from_y": {
                                "type": "number",
                                "description": "Starting Y coordinate",
                            },
                            "to_x": {
                                "type": "number",
                                "description": "Ending X coordinate",
                            },
                            "to_y": {
                                "type": "number",
                                "description": "Ending Y coordinate",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration of drag in seconds (use 0.5-1.0 for smooth visible drag)",
                                "default": 0.5,
                            },
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "description": "Mouse button to use for dragging",
                                "default": "left",
                            },
                        },
                        "required": ["from_x", "from_y", "to_x", "to_y"],
                    },
                ),
                Tool(
                    name="scroll",
                    description="Scroll up or down on a page or within an application. Use for scrolling through documents, web pages, lists, or any scrollable content on the user's screen.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Scroll amount (positive = scroll up, negative = scroll down). Typical values: 3-5 for small scroll, 10+ for larger scroll",
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate to scroll at (optional, scrolls at current cursor position if not provided)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to scroll at (optional, scrolls at current cursor position if not provided)",
                            },
                        },
                        "required": ["amount"],
                    },
                ),
                Tool(
                    name="get_screen_size",
                    description="Get the user's screen dimensions (width and height in pixels). Use this to understand screen bounds before moving cursor or to calculate positions relative to screen size.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="screenshot",
                    description="Take a full screen screenshot to see what's currently on the user's screen. Use this to see the current state of the desktop, find UI elements, verify actions completed successfully, or help the user with anything visual on their screen.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="keyboard_shortcut",
                    description="Send a keyboard shortcut (hotkey combination) like Cmd+C, Cmd+V, Cmd+Tab. Use this to copy, paste, switch apps, save files, undo/redo, or any keyboard shortcut the user would type. On macOS, use 'command' for Cmd key, 'option' for Option/Alt, 'control' for Control, 'shift' for Shift.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of keys to press together. Examples: ['command', 'c'] for copy, ['command', 'v'] for paste, ['command', 'tab'] to switch apps, ['command', 'shift', '4'] for screenshot selection",
                            },
                        },
                        "required": ["keys"],
                    },
                ),
                Tool(
                    name="key_press",
                    description="Press a single key one or more times. Use for pressing Enter, Escape, Tab, arrow keys, function keys, or typing individual characters. Good for navigating dialogs, confirming actions, or pressing special keys.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "The key to press. Examples: 'enter', 'escape', 'tab', 'space', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'f1'-'f12', or single characters like 'a', 'b', '1'",
                            },
                            "presses": {
                                "type": "number",
                                "description": "Number of times to press the key (default: 1)",
                                "default": 1,
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between presses in seconds (default: 0.1)",
                                "default": 0.1,
                            },
                        },
                        "required": ["key"],
                    },
                ),
                Tool(
                    name="type_text",
                    description="Type text character by character, simulating keyboard typing. Use for entering text into text fields, search boxes, forms, or anywhere text input is needed. For special characters or non-ASCII text, consider using clipboard paste instead.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to type",
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between keystrokes in seconds (default: 0.05)",
                                "default": 0.05,
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="open_app",
                    description="Open an application on macOS using Spotlight search (Command+Space). Use this to launch any application by name - just provide the app name like 'Safari', 'Terminal', 'Finder', 'Chrome', etc. This is the fastest way to open apps without needing to know their location.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "The name of the application to open (e.g., 'Safari', 'Terminal', 'Visual Studio Code')",
                            },
                            "delay": {
                                "type": "number",
                                "description": "Time to wait for Spotlight to appear before typing (default: 0.5s, max: 1.0s)",
                                "default": 0.5,
                                "maximum": 1.0,
                            },
                        },
                        "required": ["app_name"],
                    },
                ),
                Tool(
                    name="screenshot_with_grid",
                    description="Take a screenshot with a labeled grid overlay for precise targeting. The screen is divided into a grid (default 10x10) with cells labeled like a spreadsheet: columns A-Z (then AA, AB...), rows 1-N. Cell 'A1' is top-left. Use this BEFORE clicking when you need precise positioning - examine the grid to find which cell contains your target, then use click_grid_cell.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (default: 10). More rows = smaller cells = more precision.",
                                "default": 10,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (default: 10). More columns = smaller cells = more precision.",
                                "default": 10,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="click_grid_cell",
                    description="Click at the center of a grid cell identified by its label (e.g., 'A1', 'B3', 'C5'). Use screenshot_with_grid first to see the grid, then click the cell containing your target. The grid dimensions must match those used in screenshot_with_grid.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Grid cell label to click (e.g., 'A1', 'B3', 'C5'). Column letters + row number.",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (must match screenshot_with_grid)",
                                "default": 10,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (must match screenshot_with_grid)",
                                "default": 10,
                            },
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "description": "Mouse button to click",
                                "default": "left",
                            },
                            "clicks": {
                                "type": "number",
                                "description": "Number of clicks (use 2 for double-click)",
                                "default": 1,
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between clicks in seconds",
                                "default": 0.1,
                            },
                        },
                        "required": ["label"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[Union[TextContent, ImageContent]]:
            """Handle tool calls."""
            log(f"Tool called: {name}", "TOOL")
            if arguments:
                # Format arguments for logging (truncate long values)
                log_args = {}
                for k, v in arguments.items():
                    if isinstance(v, str) and len(v) > 50:
                        log_args[k] = v[:47] + "..."
                    else:
                        log_args[k] = v
                log(f"  Arguments: {log_args}", "DEBUG")

            try:
                if name == "get_cursor_position":
                    x, y = self.mouse.get_cursor_position()
                    result_text = f"Current cursor position: x={x}, y={y}"
                    log(f"  Result: ({x}, {y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=result_text,
                        )
                    ]

                elif name == "move_cursor":
                    x = int(arguments["x"])
                    y = int(arguments["y"])
                    # Only pass duration if explicitly provided, otherwise use default (0.3s)
                    if "duration" in arguments:
                        duration = float(arguments["duration"])
                        self.mouse.move_cursor(x, y, duration)
                    else:
                        self.mouse.move_cursor(x, y)
                    log(f"  Moved to ({x}, {y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Moved cursor to x={x}, y={y}",
                        )
                    ]

                elif name == "click":
                    x = int(arguments["x"]) if "x" in arguments else None
                    y = int(arguments["y"]) if "y" in arguments else None
                    button = arguments.get("button", "left")
                    clicks = int(arguments.get("clicks", 1))
                    interval = float(arguments.get("interval", 0.1))

                    self.mouse.click(x, y, button, clicks, interval)

                    position_str = f"at x={x}, y={y}" if x is not None and y is not None else "at current position"
                    click_type = "double-click" if clicks == 2 else f"{clicks} click(s)"
                    log(f"  {click_type} ({button}) {position_str}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Performed {click_type} with {button} button {position_str}",
                        )
                    ]

                elif name == "drag":
                    from_x = int(arguments["from_x"])
                    from_y = int(arguments["from_y"])
                    to_x = int(arguments["to_x"])
                    to_y = int(arguments["to_y"])
                    duration = float(arguments.get("duration", 0.5))
                    button = arguments.get("button", "left")

                    self.mouse.drag(from_x, from_y, to_x, to_y, duration, button)
                    log(f"  Dragged ({from_x},{from_y}) -> ({to_x},{to_y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Dragged with {button} button from ({from_x}, {from_y}) to ({to_x}, {to_y})",
                        )
                    ]

                elif name == "scroll":
                    amount = int(arguments["amount"])
                    x = int(arguments["x"]) if "x" in arguments else None
                    y = int(arguments["y"]) if "y" in arguments else None

                    self.mouse.scroll(amount, x, y)

                    position_str = f"at x={x}, y={y}" if x is not None and y is not None else "at current position"
                    direction = "up" if amount > 0 else "down"
                    log(f"  Scrolled {direction} by {abs(amount)}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Scrolled {direction} by {abs(amount)} {position_str}",
                        )
                    ]

                elif name == "get_screen_size":
                    width, height = self.mouse.get_screen_size()
                    log(f"  Screen: {width}x{height}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Screen size: width={width}, height={height}",
                        )
                    ]

                elif name == "screenshot":
                    image_base64 = self.mouse.screenshot()
                    log(f"  Screenshot captured ({len(image_base64)} bytes)", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text="Full screen screenshot:",
                        ),
                        ImageContent(
                            type="image",
                            data=image_base64,
                            mimeType="image/png",
                        ),
                    ]

                elif name == "keyboard_shortcut":
                    keys = arguments["keys"]
                    if not keys or not isinstance(keys, list):
                        raise ValueError("keys must be a non-empty list of key names")
                    self.mouse.keyboard_shortcut(*keys)
                    keys_str = "+".join(keys)
                    log(f"  Shortcut: {keys_str}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Pressed keyboard shortcut: {keys_str}",
                        )
                    ]

                elif name == "key_press":
                    key = arguments["key"]
                    presses = int(arguments.get("presses", 1))
                    interval = float(arguments.get("interval", 0.1))
                    self.mouse.key_press(key, presses, interval)
                    press_str = f" x{presses}" if presses > 1 else ""
                    log(f"  Key: {key}{press_str}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Pressed key: {key} {f'{presses} time(s)' if presses > 1 else ''}".strip(),
                        )
                    ]

                elif name == "type_text":
                    text = arguments["text"]
                    interval = float(arguments.get("interval", 0.05))
                    self.mouse.type_text(text, interval)
                    # Truncate displayed text if too long
                    display_text = text if len(text) <= 50 else text[:47] + "..."
                    log(f"  Typed: {display_text}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Typed text: {display_text}",
                        )
                    ]

                elif name == "open_app":
                    app_name = arguments["app_name"]
                    delay = float(arguments.get("delay", 0.5))
                    self.mouse.open_app(app_name, delay)
                    log(f"  Opening: {app_name}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=f"Opened Spotlight and searched for: {app_name}",
                        )
                    ]

                elif name == "screenshot_with_grid":
                    rows = int(arguments.get("rows", 10))
                    cols = int(arguments.get("cols", 10))
                    result = self.mouse.screenshot_with_grid(rows, cols)
                    log(f"  Grid screenshot: {rows}x{cols} ({result['cell_width']:.0f}x{result['cell_height']:.0f} cells)", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Screenshot with {rows}x{cols} grid overlay. "
                                f"Cell size: {result['cell_width']:.0f}x{result['cell_height']:.0f} pixels. "
                                f"Labels: columns A-{chr(ord('A') + min(cols - 1, 25))}{'...' if cols > 26 else ''}, rows 1-{rows}. "
                                f"Use click_grid_cell with a label like 'A1', 'B3', etc. to click a cell."
                            ),
                        ),
                        ImageContent(
                            type="image",
                            data=result["image"],
                            mimeType="image/png",
                        ),
                    ]

                elif name == "click_grid_cell":
                    label = arguments["label"]
                    rows = int(arguments.get("rows", 10))
                    cols = int(arguments.get("cols", 10))
                    button = arguments.get("button", "left")
                    clicks = int(arguments.get("clicks", 1))
                    interval = float(arguments.get("interval", 0.1))

                    x, y = self.mouse.click_grid_cell(
                        label, rows, cols, button, clicks, interval
                    )
                    click_type = "double-click" if clicks == 2 else f"{clicks} click(s)"
                    log(f"  Grid click: {label.upper()} -> ({x}, {y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Clicked grid cell {label.upper()} at pixel coordinates ({x}, {y}) "
                                f"with {button} button ({click_type})"
                            ),
                        )
                    ]

                else:
                    log(f"  Unknown tool: {name}", "WARN")
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown tool: {name}",
                        )
                    ]

            except ValueError as e:
                log(f"  Error: {str(e)}", "ERROR")
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}",
                    )
                ]
            except Exception as e:
                log(f"  Unexpected error: {str(e)}", "ERROR")
                return [
                    TextContent(
                        type="text",
                        text=f"Unexpected error: {str(e)}",
                    )
                ]

    async def run(self):
        """Run the server."""
        log("Server starting - waiting for connections...", "INFO")
        async with stdio_server() as (read_stream, write_stream):
            log("Client connected", "INFO")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
        log("Server shutting down", "INFO")


def main():
    """Main entry point."""
    server = MouseControlServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
