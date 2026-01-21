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

    def _build_targeting_guidance(self, target: str, rows: int, cols: int, result: dict) -> str:
        """Build intelligent targeting guidance for the AI."""
        # Determine screen zones
        zones = {
            "menu_bar": f"Row 1 (A1-{self.mouse._get_grid_label(0, cols-1)})",
            "dock": f"Row {rows} (bottom row, typically A{rows}-{self.mouse._get_grid_label(rows-1, cols-1)})",
            "center": f"Around {self.mouse._get_grid_label(rows//2, cols//2)}",
            "left_side": f"Columns A-{chr(ord('A') + cols//4)}",
            "right_side": f"Columns {chr(ord('A') + 3*cols//4)}-{self.mouse._get_grid_label(0, cols-1).rstrip('0123456789')}",
        }

        guidance = f"""TARGET LOCATION TASK: Find and click "{target}"

GRID INFO:
- Grid: {rows}x{cols} ({rows * cols} cells)
- Cell size: {result['cell_width']:.0f}x{result['cell_height']:.0f} pixels
- Screen: {result['screen_width']}x{result['screen_height']}

SCREEN ZONES (macOS):
- Menu bar: {zones['menu_bar']} (Apple menu, app menus, status icons)
- Dock: {zones['dock']} (app icons at bottom/side)
- Center: {zones['center']} (main content area)

TARGETING STRATEGY:
1. Scan the screenshot grid to locate "{target}"
2. Identify the cell label (e.g., 'B3', 'F7') that contains the target
3. If target spans multiple cells, pick the cell closest to its center
4. If target is small within a cell, consider using refine_target for precision
5. Use click_grid_cell with the identified label

COMMON PATTERNS:
- Close/minimize/maximize buttons: Usually top-left of windows (red/yellow/green)
- Dock icons: Bottom row, evenly spaced
- Menu items: Top row, left-aligned
- Dialog buttons: Bottom-center of dialogs (OK, Cancel, etc.)

After identifying the cell, respond with which cell to click and why."""

        return guidance

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
                    description="Take a screenshot with a labeled grid overlay. This is the PRIMARY tool for seeing the screen - ALWAYS use this before clicking. The screen is divided into a grid (default 12x12) with cells labeled like a spreadsheet: columns A-Z, rows 1-N. Cell 'A1' is top-left. After examining the grid, use click_grid_cell to click the cell containing your target element.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (default: 12). More rows = smaller cells = more precision.",
                                "default": 12,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (default: 12). More columns = smaller cells = more precision.",
                                "default": 12,
                            },
                        },
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
                    description="DEPRECATED: Use 'screenshot' instead (it now always includes a grid). This tool remains for compatibility but is identical to screenshot.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (default: 12).",
                                "default": 12,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (default: 12).",
                                "default": 12,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="click_grid_cell",
                    description="Click at the center of a grid cell identified by its label (e.g., 'A1', 'B3', 'C5'). Use screenshot first to see the grid, then click the cell containing your target. The grid dimensions must match those used in screenshot.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Grid cell label to click (e.g., 'A1', 'B3', 'C5'). Column letters + row number.",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (must match screenshot)",
                                "default": 12,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (must match screenshot)",
                                "default": 12,
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
                Tool(
                    name="locate_and_click",
                    description="INTELLIGENT TARGETING: Takes a screenshot with grid and a description of the target element. Use this when you need to find and click something specific on screen. Provide a clear description of what to click (e.g., 'the Safari icon in the dock', 'the close button on the dialog', 'the search field'). Returns a grid screenshot with targeting guidance.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Description of what to click (e.g., 'the red close button', 'Safari icon in dock', 'Submit button')",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Grid rows for precision (default: 12, use 20+ for small targets)",
                                "default": 12,
                            },
                            "cols": {
                                "type": "number",
                                "description": "Grid columns for precision (default: 12, use 20+ for small targets)",
                                "default": 12,
                            },
                        },
                        "required": ["target"],
                    },
                ),
                Tool(
                    name="refine_target",
                    description="PRECISION REFINEMENT: Zoom into a specific grid cell with a finer sub-grid for precise targeting. Use this after screenshot when you've identified the general area but need more precision (e.g., clicking a small button within a cell). Returns a zoomed view of just that cell with its own grid.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cell": {
                                "type": "string",
                                "description": "The cell to zoom into (e.g., 'B3')",
                            },
                            "parent_rows": {
                                "type": "number",
                                "description": "Rows in the parent grid (must match previous screenshot)",
                                "default": 12,
                            },
                            "parent_cols": {
                                "type": "number",
                                "description": "Columns in the parent grid (must match previous screenshot)",
                                "default": 12,
                            },
                            "sub_rows": {
                                "type": "number",
                                "description": "Rows in the sub-grid (default: 5)",
                                "default": 5,
                            },
                            "sub_cols": {
                                "type": "number",
                                "description": "Columns in the sub-grid (default: 5)",
                                "default": 5,
                            },
                        },
                        "required": ["cell"],
                    },
                ),
                Tool(
                    name="click_refined_cell",
                    description="Click a cell within a refined/zoomed view. Use after refine_target to click a specific sub-cell within the zoomed area.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "parent_cell": {
                                "type": "string",
                                "description": "The parent cell that was refined (e.g., 'B3')",
                            },
                            "sub_cell": {
                                "type": "string",
                                "description": "The sub-cell to click within the refined area (e.g., 'A2')",
                            },
                            "parent_rows": {
                                "type": "number",
                                "description": "Rows in the parent grid",
                                "default": 12,
                            },
                            "parent_cols": {
                                "type": "number",
                                "description": "Columns in the parent grid",
                                "default": 12,
                            },
                            "sub_rows": {
                                "type": "number",
                                "description": "Rows in the sub-grid",
                                "default": 5,
                            },
                            "sub_cols": {
                                "type": "number",
                                "description": "Columns in the sub-grid",
                                "default": 5,
                            },
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "description": "Mouse button to click",
                                "default": "left",
                            },
                            "clicks": {
                                "type": "number",
                                "description": "Number of clicks",
                                "default": 1,
                            },
                        },
                        "required": ["parent_cell", "sub_cell"],
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
                    rows = int(arguments.get("rows", 12))
                    cols = int(arguments.get("cols", 12))
                    result = self.mouse.screenshot_with_grid(rows, cols)
                    log(f"  Grid screenshot: {rows}x{cols} ({result['cell_width']:.0f}x{result['cell_height']:.0f} cells)", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Screenshot with {rows}x{cols} grid overlay. "
                                f"Cell size: {result['cell_width']:.0f}x{result['cell_height']:.0f} pixels. "
                                f"Screen: {result['screen_width']}x{result['screen_height']}. "
                                f"Labels: columns A-{self.mouse._get_grid_label(0, cols - 1).rstrip('0123456789')}, rows 1-{rows}. "
                                f"To click a target, identify which cell contains it and use click_grid_cell with that label."
                            ),
                        ),
                        ImageContent(
                            type="image",
                            data=result["image"],
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
                    # Deprecated: redirects to screenshot behavior
                    rows = int(arguments.get("rows", 12))
                    cols = int(arguments.get("cols", 12))
                    result = self.mouse.screenshot_with_grid(rows, cols)
                    log(f"  Grid screenshot (legacy): {rows}x{cols}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"[DEPRECATED: Use 'screenshot' instead] "
                                f"Screenshot with {rows}x{cols} grid overlay. "
                                f"Cell size: {result['cell_width']:.0f}x{result['cell_height']:.0f} pixels. "
                                f"To click a target, use click_grid_cell with the cell label."
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
                    rows = int(arguments.get("rows", 12))
                    cols = int(arguments.get("cols", 12))
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

                elif name == "locate_and_click":
                    target = arguments["target"]
                    rows = int(arguments.get("rows", 12))
                    cols = int(arguments.get("cols", 12))
                    result = self.mouse.screenshot_with_grid(rows, cols)
                    log(f"  Locate target: '{target}' ({rows}x{cols} grid)", "TOOL")

                    # Build targeting guidance
                    guidance = self._build_targeting_guidance(target, rows, cols, result)

                    return [
                        TextContent(
                            type="text",
                            text=guidance,
                        ),
                        ImageContent(
                            type="image",
                            data=result["image"],
                            mimeType="image/png",
                        ),
                    ]

                elif name == "refine_target":
                    cell = arguments["cell"]
                    parent_rows = int(arguments.get("parent_rows", 12))
                    parent_cols = int(arguments.get("parent_cols", 12))
                    sub_rows = int(arguments.get("sub_rows", 5))
                    sub_cols = int(arguments.get("sub_cols", 5))

                    result = self.mouse.screenshot_refined_cell(
                        cell, parent_rows, parent_cols, sub_rows, sub_cols
                    )
                    log(f"  Refine: {cell.upper()} -> {sub_rows}x{sub_cols} sub-grid", "TOOL")

                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Zoomed into cell {cell.upper()} with {sub_rows}x{sub_cols} sub-grid. "
                                f"Sub-cell size: {result['sub_cell_width']:.0f}x{result['sub_cell_height']:.0f} pixels. "
                                f"Parent cell bounds: ({result['cell_x']}, {result['cell_y']}) to "
                                f"({result['cell_x'] + result['cell_width']:.0f}, {result['cell_y'] + result['cell_height']:.0f}). "
                                f"Use click_refined_cell with parent_cell='{cell.upper()}' and the sub_cell label to click."
                            ),
                        ),
                        ImageContent(
                            type="image",
                            data=result["image"],
                            mimeType="image/png",
                        ),
                    ]

                elif name == "click_refined_cell":
                    parent_cell = arguments["parent_cell"]
                    sub_cell = arguments["sub_cell"]
                    parent_rows = int(arguments.get("parent_rows", 12))
                    parent_cols = int(arguments.get("parent_cols", 12))
                    sub_rows = int(arguments.get("sub_rows", 5))
                    sub_cols = int(arguments.get("sub_cols", 5))
                    button = arguments.get("button", "left")
                    clicks = int(arguments.get("clicks", 1))

                    x, y = self.mouse.click_refined_cell(
                        parent_cell, sub_cell,
                        parent_rows, parent_cols,
                        sub_rows, sub_cols,
                        button, clicks
                    )
                    click_type = "double-click" if clicks == 2 else f"{clicks} click(s)"
                    log(f"  Refined click: {parent_cell.upper()}/{sub_cell.upper()} -> ({x}, {y})", "INFO")

                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Clicked sub-cell {sub_cell.upper()} within {parent_cell.upper()} "
                                f"at pixel coordinates ({x}, {y}) with {button} button ({click_type})"
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
