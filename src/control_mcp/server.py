"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional, Union, Dict, Any
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .mouse_control import MouseController
from .log_window import start_log_window, log

# Try to import accessibility module (may fail if pyobjc not installed)
try:
    from .accessibility import (
        AccessibilityController,
        ACCESSIBILITY_AVAILABLE,
        ROLE_BUTTON,
        ROLE_CHECKBOX,
        ROLE_LINK,
        ROLE_MENU_ITEM,
        ROLE_TEXT_FIELD,
        ROLE_STATIC_TEXT,
        ROLE_POP_UP_BUTTON,
    )
except ImportError:
    ACCESSIBILITY_AVAILABLE = False
    AccessibilityController = None


def load_settings() -> Dict[str, Any]:
    """
    Load settings from settings.txt file.

    Returns:
        Dictionary with settings (pixels_per_second, use_bezier)
    """
    # Default settings
    settings = {
        "pixels_per_second": 2000.0,
        "use_bezier": True,
    }

    # Find settings.txt in the project root (parent of src)
    current_dir = Path(__file__).parent
    settings_file = current_dir.parent.parent / "settings.txt"

    if not settings_file.exists():
        return settings

    try:
        with open(settings_file, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "pixels_per_second":
                        try:
                            settings["pixels_per_second"] = float(value)
                        except ValueError:
                            pass  # Keep default

                    elif key == "use_bezier":
                        settings["use_bezier"] = value.lower() in ("true", "yes", "1", "on")

    except Exception:
        pass  # Keep defaults

    return settings


class MouseControlServer:
    """MCP server that provides mouse control tools."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("control-mcp")

        # Load settings from settings.txt
        settings = load_settings()

        # Initialize mouse controller with settings
        self.mouse = MouseController(
            pixels_per_second=settings["pixels_per_second"],
            use_bezier=settings["use_bezier"]
        )

        # Start the log window
        self.log_window = start_log_window()
        log("MCP Server initialized", "INFO")
        log(f"Screen size: {self.mouse.screen_width}x{self.mouse.screen_height}", "INFO")
        log(f"Movement: {'bezier curves' if settings['use_bezier'] else 'straight line'} at {settings['pixels_per_second']} px/s", "INFO")

        # Initialize accessibility controller if available
        self.accessibility = None
        if ACCESSIBILITY_AVAILABLE:
            try:
                self.accessibility = AccessibilityController()
                if self.accessibility.has_permissions():
                    log("Accessibility API: enabled", "INFO")
                else:
                    log("Accessibility API: no permissions (enable in System Preferences)", "WARN")
            except Exception as e:
                log(f"Accessibility API: init failed ({e})", "WARN")
        else:
            log("Accessibility API: not available (install pyobjc)", "WARN")

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
                    description="Move the mouse cursor to specific screen coordinates. IMPORTANT: ALWAYS use screenshot_with_grid FIRST to identify the target coordinates before calling this tool. Use click_grid_cell instead if you plan to click after moving. Movement duration is automatically calculated based on distance. Movements are smooth and follow a natural bezier curve.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate (pixels from left edge of screen). Get this from screenshot_with_grid by identifying the cell center.",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (pixels from top edge of screen). Get this from screenshot_with_grid by identifying the cell center.",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Optional override for movement duration in seconds. If not provided, duration is automatically calculated based on distance (default speed: 2000 pixels/second).",
                            },
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="click",
                    description="Perform mouse click using pixel coordinates. IMPORTANT: Use click_grid_cell instead (it's easier and more accurate). Only use this if you already know exact pixel coordinates. For targeting UI elements, use screenshot_with_grid + click_grid_cell.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate to click at (optional, uses current cursor position if not provided). Get from screenshot_with_grid if needed.",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to click at (optional, uses current cursor position if not provided). Get from screenshot_with_grid if needed.",
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
                    name="drag_grid_cells",
                    description="Drag from one grid cell to another. Use screenshot_with_grid first to identify the cells. Simpler than drag when working with grid coordinates.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_label": {
                                "type": "string",
                                "description": "Starting grid cell label (e.g., 'A1', 'B3')",
                            },
                            "to_label": {
                                "type": "string",
                                "description": "Ending grid cell label (e.g., 'C5', 'D10')",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/36.",
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/36.",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration of drag in seconds",
                                "default": 0.5,
                            },
                            "button": {
                                "type": "string",
                                "enum": ["left", "right", "middle"],
                                "description": "Mouse button to use for dragging",
                                "default": "left",
                            },
                        },
                        "required": ["from_label", "to_label"],
                    },
                ),
                Tool(
                    name="drag",
                    description="Drag from one position to another using pixel coordinates. IMPORTANT: Use screenshot_with_grid FIRST to identify coordinates, or use drag_grid_cells for easier grid-based dragging.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_x": {
                                "type": "number",
                                "description": "Starting X coordinate (get from screenshot_with_grid)",
                            },
                            "from_y": {
                                "type": "number",
                                "description": "Starting Y coordinate (get from screenshot_with_grid)",
                            },
                            "to_x": {
                                "type": "number",
                                "description": "Ending X coordinate (get from screenshot_with_grid)",
                            },
                            "to_y": {
                                "type": "number",
                                "description": "Ending Y coordinate (get from screenshot_with_grid)",
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
                    description="Scroll up or down at current cursor position or at specific coordinates. If providing coordinates, use screenshot_with_grid first to identify the location. Good for scrolling through documents, web pages, lists, or any scrollable content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Scroll amount (positive = scroll up, negative = scroll down). Typical values: 3-5 for small scroll, 10+ for larger scroll",
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate to scroll at (optional, scrolls at current cursor position if not provided). Use screenshot_with_grid to identify coordinates.",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to scroll at (optional, scrolls at current cursor position if not provided). Use screenshot_with_grid to identify coordinates.",
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
                    description="Take a clean screenshot to see what's currently on the user's screen. Use this to see the current state of the desktop, verify actions completed successfully, or help the user with anything visual on their screen. For clicking/targeting UI elements, use screenshot_with_grid instead.",
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
                    description="Take a screenshot with a labeled grid overlay for precise targeting. ALWAYS use this BEFORE clicking to locate UI elements. The screen is divided into a fine grid (default: rows=screen_height/36, cols=screen_width/36, creating ~36x36 pixel cells). Cells are labeled like a spreadsheet: columns A-Z (then AA, AB...), rows 1-N. Cell 'A1' is top-left. After examining the grid, use click_grid_cell to click the cell containing your target.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid. Default is screen_height/36 for ~36px tall cells.",
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid. Default is screen_width/36 for ~36px wide cells.",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="move_to_grid_cell",
                    description="Move cursor to the center of a grid cell identified by its label (e.g., 'A1', 'B3', 'ZZ500'). Use screenshot_with_grid first to identify the target cell. This moves without clicking - use click_grid_cell if you want to click after moving.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Grid cell label to move to (e.g., 'A1', 'B3', 'AA100'). Column letters + row number.",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/36.",
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/36.",
                            },
                        },
                        "required": ["label"],
                    },
                ),
                Tool(
                    name="click_grid_cell",
                    description="Click at the center of a grid cell identified by its label (e.g., 'A1', 'B3', 'ZZ500'). Use screenshot_with_grid first to see the grid, then click the cell containing your target. The grid dimensions must match those used in screenshot_with_grid.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Grid cell label to click (e.g., 'A1', 'B3', 'AA100'). Column letters + row number.",
                            },
                            "rows": {
                                "type": "number",
                                "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/36.",
                            },
                            "cols": {
                                "type": "number",
                                "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/36.",
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
                                "description": "Grid rows for precision. Default is screen_height/36.",
                            },
                            "cols": {
                                "type": "number",
                                "description": "Grid columns for precision. Default is screen_width/36.",
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
                                "description": "Rows in the parent grid (must match previous screenshot). Default is screen_height/36.",
                            },
                            "parent_cols": {
                                "type": "number",
                                "description": "Columns in the parent grid (must match previous screenshot). Default is screen_width/36.",
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
                                "description": "Rows in the parent grid. Default is screen_height/36.",
                            },
                            "parent_cols": {
                                "type": "number",
                                "description": "Columns in the parent grid. Default is screen_width/36.",
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
                # Accessibility API Tools
                Tool(
                    name="click_button",
                    description="ACCESSIBILITY API: Click a button by its text label using macOS Accessibility API. This is more reliable than coordinate-based clicking as it uses the native UI element interaction. Requires accessibility permissions to be enabled in System Preferences > Privacy & Security > Accessibility.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Exact button title to click (e.g., 'OK', 'Cancel', 'Save')",
                            },
                            "title_contains": {
                                "type": "string",
                                "description": "Substring to match in button title (case-insensitive). Use this for partial matches like 'Save' to match 'Save As...'",
                            },
                            "in_focused_window": {
                                "type": "boolean",
                                "description": "Only search in the focused window (default: true). Set to false to search entire application.",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="find_buttons",
                    description="ACCESSIBILITY API: Find all buttons in the current window or application. Returns button titles, positions, and enabled states. Use this to discover available buttons before clicking.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title_contains": {
                                "type": "string",
                                "description": "Optional filter: only return buttons containing this text in their title",
                            },
                            "in_focused_window": {
                                "type": "boolean",
                                "description": "Only search in focused window (default: true)",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="find_ui_elements",
                    description="ACCESSIBILITY API: Find UI elements by role and/or title. Useful for discovering interactive elements like checkboxes, text fields, links, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Element role to search for. Common values: 'AXButton', 'AXCheckBox', 'AXTextField', 'AXStaticText', 'AXLink', 'AXMenuItem', 'AXPopUpButton'",
                            },
                            "title": {
                                "type": "string",
                                "description": "Exact title to match",
                            },
                            "title_contains": {
                                "type": "string",
                                "description": "Substring to match in title (case-insensitive)",
                            },
                            "in_focused_window": {
                                "type": "boolean",
                                "description": "Only search in focused window (default: true)",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="click_ui_element",
                    description="ACCESSIBILITY API: Click any UI element by its role and title. Use find_ui_elements first to discover elements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Element role (e.g., 'AXButton', 'AXCheckBox', 'AXLink', 'AXMenuItem')",
                            },
                            "title": {
                                "type": "string",
                                "description": "Exact element title",
                            },
                            "title_contains": {
                                "type": "string",
                                "description": "Substring to match in title",
                            },
                            "in_focused_window": {
                                "type": "boolean",
                                "description": "Only search in focused window (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["role"],
                    },
                ),
                Tool(
                    name="click_menu_item",
                    description="ACCESSIBILITY API: Click a menu item by navigating the menu path. Provide the path from menu bar to the item.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "menu_path": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Path from menu bar to item. Example: ['File', 'Save As...'] or ['Edit', 'Find', 'Find...']",
                            },
                        },
                        "required": ["menu_path"],
                    },
                ),
                Tool(
                    name="get_element_at_position",
                    description="ACCESSIBILITY API: Get information about the UI element at a specific screen position. Useful for understanding what's under the cursor.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate",
                            },
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="get_focused_window_info",
                    description="ACCESSIBILITY API: Get information about the currently focused window and application.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="get_ui_tree",
                    description="ACCESSIBILITY API: Get a hierarchical tree of UI elements. Useful for understanding the structure of a window.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "in_focused_window": {
                                "type": "boolean",
                                "description": "Only get elements in focused window (default: true)",
                                "default": True,
                            },
                            "max_depth": {
                                "type": "number",
                                "description": "Maximum depth to traverse (default: 3, max: 10)",
                                "default": 3,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="check_accessibility_permissions",
                    description="Check if accessibility permissions are granted. Returns instructions for enabling if not.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
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

                elif name == "drag_grid_cells":
                    from_label = arguments["from_label"]
                    to_label = arguments["to_label"]
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    rows = int(arguments.get("rows", default_rows))
                    cols = int(arguments.get("cols", default_cols))
                    duration = float(arguments.get("duration", 0.5))
                    button = arguments.get("button", "left")

                    from_x, from_y = self.mouse.get_grid_cell_center(from_label, rows, cols)
                    to_x, to_y = self.mouse.get_grid_cell_center(to_label, rows, cols)
                    self.mouse.drag(from_x, from_y, to_x, to_y, duration, button)
                    log(f"  Grid drag: {from_label.upper()} -> {to_label.upper()} ({from_x},{from_y}) -> ({to_x},{to_y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Dragged with {button} button from grid cell {from_label.upper()} ({from_x}, {from_y}) "
                                f"to grid cell {to_label.upper()} ({to_x}, {to_y})"
                            ),
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
                            text="Clean screenshot of current screen state:",
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
                    # Default to screen dimensions divided by 36 for ~36x36 pixel cells
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    rows = int(arguments.get("rows", default_rows))
                    cols = int(arguments.get("cols", default_cols))
                    result = self.mouse.screenshot_with_grid(rows, cols)
                    log(f"  Grid screenshot: {rows}x{cols} ({result['cell_width']:.0f}x{result['cell_height']:.0f} cells)", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Screenshot with {rows}x{cols} grid overlay for targeting. "
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

                elif name == "move_to_grid_cell":
                    label = arguments["label"]
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    rows = int(arguments.get("rows", default_rows))
                    cols = int(arguments.get("cols", default_cols))

                    x, y = self.mouse.get_grid_cell_center(label, rows, cols)
                    self.mouse.move_cursor(x, y)
                    log(f"  Grid move: {label.upper()} -> ({x}, {y})", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"Moved cursor to grid cell {label.upper()} at pixel coordinates ({x}, {y})"
                            ),
                        )
                    ]

                elif name == "click_grid_cell":
                    label = arguments["label"]
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    rows = int(arguments.get("rows", default_rows))
                    cols = int(arguments.get("cols", default_cols))
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
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    rows = int(arguments.get("rows", default_rows))
                    cols = int(arguments.get("cols", default_cols))
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
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    parent_rows = int(arguments.get("parent_rows", default_rows))
                    parent_cols = int(arguments.get("parent_cols", default_cols))
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
                    default_rows = self.mouse.screen_height // 36
                    default_cols = self.mouse.screen_width // 36
                    parent_rows = int(arguments.get("parent_rows", default_rows))
                    parent_cols = int(arguments.get("parent_cols", default_cols))
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

                # Accessibility API Tools
                elif name == "check_accessibility_permissions":
                    if not ACCESSIBILITY_AVAILABLE:
                        log("  Accessibility: pyobjc not installed", "WARN")
                        return [
                            TextContent(
                                type="text",
                                text=(
                                    "Accessibility API not available. "
                                    "Install pyobjc packages: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Quartz pyobjc-framework-Cocoa"
                                ),
                            )
                        ]

                    has_perms = self.accessibility.has_permissions() if self.accessibility else False
                    if has_perms:
                        log("  Accessibility: permissions granted", "INFO")
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility permissions are granted. All accessibility tools are available.",
                            )
                        ]
                    else:
                        log("  Accessibility: permissions NOT granted", "WARN")
                        return [
                            TextContent(
                                type="text",
                                text=(
                                    "Accessibility permissions NOT granted. To enable:\n"
                                    "1. Open System Preferences (System Settings on macOS 13+)\n"
                                    "2. Go to Privacy & Security > Accessibility\n"
                                    "3. Add and enable the terminal/application running this MCP server\n"
                                    "4. Restart the MCP server after granting permissions"
                                ),
                            )
                        ]

                elif name == "click_button":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    title = arguments.get("title")
                    title_contains = arguments.get("title_contains")
                    in_focused_window = arguments.get("in_focused_window", True)

                    if not title and not title_contains:
                        return [
                            TextContent(
                                type="text",
                                text="Error: Must specify either 'title' (exact match) or 'title_contains' (substring match)",
                            )
                        ]

                    result = self.accessibility.click_button(
                        title=title,
                        title_contains=title_contains,
                        in_focused_window=in_focused_window,
                    )

                    if result["success"]:
                        button_info = result.get("button", {})
                        log(f"  Clicked button: {button_info.get('title', 'unknown')}", "INFO")
                        return [
                            TextContent(
                                type="text",
                                text=f"Successfully clicked button: '{button_info.get('title', 'unknown')}'",
                            )
                        ]
                    else:
                        log(f"  Button click failed: {result.get('error')}", "WARN")
                        return [
                            TextContent(
                                type="text",
                                text=f"Failed to click button: {result.get('error')}",
                            )
                        ]

                elif name == "find_buttons":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    title_contains = arguments.get("title_contains")
                    in_focused_window = arguments.get("in_focused_window", True)

                    buttons = self.accessibility.find_buttons(
                        title_contains=title_contains,
                        in_focused_window=in_focused_window,
                    )

                    log(f"  Found {len(buttons)} buttons", "INFO")

                    if not buttons:
                        return [
                            TextContent(
                                type="text",
                                text="No buttons found in the current window.",
                            )
                        ]

                    # Format buttons for display
                    lines = [f"Found {len(buttons)} button(s):"]
                    for i, btn in enumerate(buttons[:30], 1):  # Limit to 30
                        title = btn.get("title") or "(no title)"
                        enabled = "enabled" if btn.get("enabled", True) else "disabled"
                        pos = btn.get("position", {})
                        pos_str = f"at ({pos.get('x', '?')}, {pos.get('y', '?')})" if pos else ""
                        lines.append(f"  {i}. \"{title}\" [{enabled}] {pos_str}")

                    if len(buttons) > 30:
                        lines.append(f"  ... and {len(buttons) - 30} more")

                    return [
                        TextContent(
                            type="text",
                            text="\n".join(lines),
                        )
                    ]

                elif name == "find_ui_elements":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    role = arguments.get("role")
                    title = arguments.get("title")
                    title_contains = arguments.get("title_contains")
                    in_focused_window = arguments.get("in_focused_window", True)

                    elements = self.accessibility.find_elements(
                        role=role,
                        title=title,
                        title_contains=title_contains,
                        in_focused_window=in_focused_window,
                    )

                    log(f"  Found {len(elements)} elements (role={role})", "INFO")

                    if not elements:
                        return [
                            TextContent(
                                type="text",
                                text=f"No elements found matching criteria (role={role}, title={title or title_contains}).",
                            )
                        ]

                    # Format elements for display
                    lines = [f"Found {len(elements)} element(s):"]
                    for i, elem in enumerate(elements[:30], 1):
                        role_str = elem.get("role", "unknown")
                        title_str = elem.get("title") or elem.get("description") or "(no title)"
                        enabled = "enabled" if elem.get("enabled", True) else "disabled"
                        pos = elem.get("position", {})
                        pos_str = f"at ({pos.get('x', '?')}, {pos.get('y', '?')})" if pos else ""
                        lines.append(f"  {i}. [{role_str}] \"{title_str}\" [{enabled}] {pos_str}")

                    if len(elements) > 30:
                        lines.append(f"  ... and {len(elements) - 30} more")

                    return [
                        TextContent(
                            type="text",
                            text="\n".join(lines),
                        )
                    ]

                elif name == "click_ui_element":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    role = arguments["role"]
                    title = arguments.get("title")
                    title_contains = arguments.get("title_contains")
                    in_focused_window = arguments.get("in_focused_window", True)

                    result = self.accessibility.click_element(
                        role=role,
                        title=title,
                        title_contains=title_contains,
                        in_focused_window=in_focused_window,
                    )

                    if result["success"]:
                        elem_info = result.get("element", {})
                        log(f"  Clicked element: {elem_info.get('role')} - {elem_info.get('title')}", "INFO")
                        return [
                            TextContent(
                                type="text",
                                text=f"Successfully clicked {elem_info.get('role')}: '{elem_info.get('title', 'unknown')}'",
                            )
                        ]
                    else:
                        log(f"  Element click failed: {result.get('error')}", "WARN")
                        return [
                            TextContent(
                                type="text",
                                text=f"Failed to click element: {result.get('error')}",
                            )
                        ]

                elif name == "click_menu_item":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    menu_path = arguments["menu_path"]
                    if not menu_path or not isinstance(menu_path, list):
                        return [
                            TextContent(
                                type="text",
                                text="Error: menu_path must be a non-empty list of menu titles",
                            )
                        ]

                    result = self.accessibility.click_menu_item(menu_path)

                    if result["success"]:
                        log(f"  Clicked menu: {' > '.join(menu_path)}", "INFO")
                        return [
                            TextContent(
                                type="text",
                                text=f"Successfully clicked menu item: {' > '.join(menu_path)}",
                            )
                        ]
                    else:
                        log(f"  Menu click failed: {result.get('error')}", "WARN")
                        return [
                            TextContent(
                                type="text",
                                text=f"Failed to click menu item: {result.get('error')}",
                            )
                        ]

                elif name == "get_element_at_position":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    x = int(arguments["x"])
                    y = int(arguments["y"])

                    elem_info = self.accessibility.get_element_at_position(x, y)

                    if elem_info:
                        log(f"  Element at ({x}, {y}): {elem_info.get('role')}", "INFO")
                        lines = [f"Element at ({x}, {y}):"]
                        lines.append(f"  Role: {elem_info.get('role', 'unknown')}")
                        if elem_info.get("title"):
                            lines.append(f"  Title: {elem_info['title']}")
                        if elem_info.get("description"):
                            lines.append(f"  Description: {elem_info['description']}")
                        if elem_info.get("value") is not None:
                            lines.append(f"  Value: {elem_info['value']}")
                        if elem_info.get("enabled") is not None:
                            lines.append(f"  Enabled: {elem_info['enabled']}")
                        if elem_info.get("position"):
                            pos = elem_info["position"]
                            lines.append(f"  Position: ({pos['x']}, {pos['y']})")
                        if elem_info.get("size"):
                            size = elem_info["size"]
                            lines.append(f"  Size: {size['width']}x{size['height']}")

                        return [
                            TextContent(
                                type="text",
                                text="\n".join(lines),
                            )
                        ]
                    else:
                        log(f"  No element at ({x}, {y})", "INFO")
                        return [
                            TextContent(
                                type="text",
                                text=f"No UI element found at position ({x}, {y})",
                            )
                        ]

                elif name == "get_focused_window_info":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    app_info = self.accessibility.get_focused_application()
                    window_result = self.accessibility.get_focused_window()

                    lines = ["Focused Application and Window:"]

                    if app_info:
                        lines.append(f"\nApplication:")
                        lines.append(f"  Title: {app_info.get('title', 'unknown')}")
                        if app_info.get("role"):
                            lines.append(f"  Role: {app_info['role']}")

                    if window_result:
                        _, window_info = window_result
                        lines.append(f"\nFocused Window:")
                        lines.append(f"  Title: {window_info.get('title', 'unknown')}")
                        if window_info.get("position"):
                            pos = window_info["position"]
                            lines.append(f"  Position: ({pos['x']}, {pos['y']})")
                        if window_info.get("size"):
                            size = window_info["size"]
                            lines.append(f"  Size: {size['width']}x{size['height']}")
                    else:
                        lines.append("\nNo focused window found")

                    log(f"  Focused: {app_info.get('title', 'unknown') if app_info else 'none'}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text="\n".join(lines),
                        )
                    ]

                elif name == "get_ui_tree":
                    if not self.accessibility:
                        return [
                            TextContent(
                                type="text",
                                text="Accessibility API not available. Use check_accessibility_permissions for details.",
                            )
                        ]

                    in_focused_window = arguments.get("in_focused_window", True)
                    max_depth = min(int(arguments.get("max_depth", 3)), 10)

                    tree = self.accessibility.get_ui_tree(
                        in_focused_window=in_focused_window,
                        max_depth=max_depth,
                    )

                    if not tree:
                        return [
                            TextContent(
                                type="text",
                                text="No UI tree available (no focused window or application)",
                            )
                        ]

                    def format_tree(node: dict, indent: int = 0) -> List[str]:
                        lines = []
                        prefix = "  " * indent
                        role = node.get("role", "unknown")
                        title = node.get("title") or node.get("description") or ""

                        # Format the node
                        node_str = f"{prefix}[{role}]"
                        if title:
                            node_str += f' "{title}"'
                        lines.append(node_str)

                        # Recurse into children
                        children = node.get("children", [])
                        for child in children[:20]:  # Limit children per level
                            lines.extend(format_tree(child, indent + 1))
                        if len(children) > 20:
                            lines.append(f"{prefix}  ... and {len(children) - 20} more children")

                        return lines

                    output_lines = ["UI Element Tree:"]
                    for root in tree:
                        output_lines.extend(format_tree(root))

                    log(f"  UI tree: {len(tree)} root(s), depth={max_depth}", "INFO")
                    return [
                        TextContent(
                            type="text",
                            text="\n".join(output_lines[:200]),  # Limit output
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
