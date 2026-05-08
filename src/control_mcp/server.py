"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional, Union, Dict, Any, List
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

    def _setup_handlers(self):
        """Set up request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available mouse control tools."""
            return [
                # Basic mouse tools
                Tool(
                    name="get_cursor_position",
                    description="Get the current mouse cursor position on the user's screen.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="move_cursor",
                    description="Move the mouse cursor to specific screen coordinates. Movement is smooth with bezier curves.",
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
                                "description": "Optional override for movement duration in seconds",
                            },
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="click",
                    description="Perform mouse click at coordinates or current position. For clicking UI elements, prefer using click_button or click_ui_element from the accessibility API.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate (optional, uses current position if not provided)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (optional, uses current position if not provided)",
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
                        "required": [],
                    },
                ),
                Tool(
                    name="drag",
                    description="Drag from one position to another using pixel coordinates.",
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
                        "required": ["from_x", "from_y", "to_x", "to_y"],
                    },
                ),
                Tool(
                    name="scroll",
                    description="Scroll up or down at current cursor position or at specific coordinates.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Scroll amount (positive = up, negative = down)",
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate (optional)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (optional)",
                            },
                        },
                        "required": ["amount"],
                    },
                ),
                Tool(
                    name="get_screen_size",
                    description="Get the screen dimensions (width and height in pixels).",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="screenshot",
                    description="Take a screenshot to see what's currently on the user's screen.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                # Keyboard tools
                Tool(
                    name="keyboard_shortcut",
                    description="Send a keyboard shortcut (hotkey combination). On macOS, use 'command' for Cmd, 'option' for Option/Alt, 'control' for Control, 'shift' for Shift.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of keys to press together. Examples: ['command', 'c'] for copy, ['command', 'v'] for paste",
                            },
                        },
                        "required": ["keys"],
                    },
                ),
                Tool(
                    name="key_press",
                    description="Press a single key one or more times.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "The key to press (e.g., 'enter', 'escape', 'tab', 'space', arrow keys, etc.)",
                            },
                            "presses": {
                                "type": "number",
                                "description": "Number of times to press the key",
                                "default": 1,
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between presses in seconds",
                                "default": 0.1,
                            },
                        },
                        "required": ["key"],
                    },
                ),
                Tool(
                    name="type_text",
                    description="Type text character by character, simulating keyboard typing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to type",
                            },
                            "interval": {
                                "type": "number",
                                "description": "Time between keystrokes in seconds",
                                "default": 0.05,
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="open_app",
                    description="Open an application on macOS using Spotlight search (Command+Space).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "The name of the application to open",
                            },
                            "delay": {
                                "type": "number",
                                "description": "Time to wait for Spotlight (default: 0.5s)",
                                "default": 0.5,
                            },
                        },
                        "required": ["app_name"],
                    },
                ),
                # Accessibility API Tools
                Tool(
                    name="click_button",
                    description="Click a button by its text label using macOS Accessibility API. More reliable than coordinate-based clicking.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Exact button title to click (e.g., 'OK', 'Cancel', 'Save')",
                            },
                            "title_contains": {
                                "type": "string",
                                "description": "Substring to match in button title (case-insensitive)",
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
                    name="find_buttons",
                    description="Find all buttons in the current window. Returns button titles, positions, and enabled states.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title_contains": {
                                "type": "string",
                                "description": "Optional filter: only return buttons containing this text",
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
                    description="Find UI elements by role and/or title. Useful for discovering interactive elements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Element role: 'AXButton', 'AXCheckBox', 'AXTextField', 'AXStaticText', 'AXLink', 'AXMenuItem', 'AXPopUpButton'",
                            },
                            "title": {
                                "type": "string",
                                "description": "Exact title to match",
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
                        "required": [],
                    },
                ),
                Tool(
                    name="click_ui_element",
                    description="Click any UI element by its role and title.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Element role (e.g., 'AXButton', 'AXCheckBox', 'AXLink')",
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
                    description="Click a menu item by navigating the menu path from the menu bar.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "menu_path": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Path from menu bar to item. Example: ['File', 'Save As...']",
                            },
                        },
                        "required": ["menu_path"],
                    },
                ),
                Tool(
                    name="get_element_at_position",
                    description="Get information about the UI element at a specific screen position.",
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
                    description="Get information about the currently focused window and application.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="get_ui_tree",
                    description="Get a hierarchical tree of UI elements in the focused window.",
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
                log_args = {k: (v[:47] + "..." if isinstance(v, str) and len(v) > 50 else v) for k, v in arguments.items()}
                log(f"  Arguments: {log_args}", "DEBUG")

            try:
                # Basic mouse tools
                if name == "get_cursor_position":
                    x, y = self.mouse.get_cursor_position()
                    log(f"  Result: ({x}, {y})", "INFO")
                    return [TextContent(type="text", text=f"Current cursor position: x={x}, y={y}")]

                elif name == "move_cursor":
                    x, y = int(arguments["x"]), int(arguments["y"])
                    duration = float(arguments["duration"]) if "duration" in arguments else None
                    if duration:
                        self.mouse.move_cursor(x, y, duration)
                    else:
                        self.mouse.move_cursor(x, y)
                    log(f"  Moved to ({x}, {y})", "INFO")
                    return [TextContent(type="text", text=f"Moved cursor to x={x}, y={y}")]

                elif name == "click":
                    x = int(arguments["x"]) if "x" in arguments else None
                    y = int(arguments["y"]) if "y" in arguments else None
                    button = arguments.get("button", "left")
                    clicks = int(arguments.get("clicks", 1))
                    interval = float(arguments.get("interval", 0.1))
                    self.mouse.click(x, y, button, clicks, interval)
                    pos_str = f"at ({x}, {y})" if x is not None else "at current position"
                    click_type = "double-click" if clicks == 2 else f"{clicks} click(s)"
                    log(f"  {click_type} ({button}) {pos_str}", "INFO")
                    return [TextContent(type="text", text=f"Performed {click_type} with {button} button {pos_str}")]

                elif name == "drag":
                    from_x, from_y = int(arguments["from_x"]), int(arguments["from_y"])
                    to_x, to_y = int(arguments["to_x"]), int(arguments["to_y"])
                    duration = float(arguments.get("duration", 0.5))
                    button = arguments.get("button", "left")
                    self.mouse.drag(from_x, from_y, to_x, to_y, duration, button)
                    log(f"  Dragged ({from_x},{from_y}) -> ({to_x},{to_y})", "INFO")
                    return [TextContent(type="text", text=f"Dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})")]

                elif name == "scroll":
                    amount = int(arguments["amount"])
                    x = int(arguments["x"]) if "x" in arguments else None
                    y = int(arguments["y"]) if "y" in arguments else None
                    self.mouse.scroll(amount, x, y)
                    direction = "up" if amount > 0 else "down"
                    log(f"  Scrolled {direction} by {abs(amount)}", "INFO")
                    return [TextContent(type="text", text=f"Scrolled {direction} by {abs(amount)}")]

                elif name == "get_screen_size":
                    width, height = self.mouse.get_screen_size()
                    log(f"  Screen: {width}x{height}", "INFO")
                    return [TextContent(type="text", text=f"Screen size: {width}x{height}")]

                elif name == "screenshot":
                    image_base64 = self.mouse.screenshot()
                    log(f"  Screenshot captured ({len(image_base64)} bytes)", "INFO")
                    return [
                        TextContent(type="text", text="Screenshot of current screen:"),
                        ImageContent(type="image", data=image_base64, mimeType="image/png"),
                    ]

                # Keyboard tools
                elif name == "keyboard_shortcut":
                    keys = arguments["keys"]
                    if not keys or not isinstance(keys, list):
                        raise ValueError("keys must be a non-empty list")
                    self.mouse.keyboard_shortcut(*keys)
                    log(f"  Shortcut: {'+'.join(keys)}", "INFO")
                    return [TextContent(type="text", text=f"Pressed: {'+'.join(keys)}")]

                elif name == "key_press":
                    key = arguments["key"]
                    presses = int(arguments.get("presses", 1))
                    interval = float(arguments.get("interval", 0.1))
                    self.mouse.key_press(key, presses, interval)
                    log(f"  Key: {key} x{presses}", "INFO")
                    return [TextContent(type="text", text=f"Pressed {key}" + (f" {presses} times" if presses > 1 else ""))]

                elif name == "type_text":
                    text = arguments["text"]
                    interval = float(arguments.get("interval", 0.05))
                    self.mouse.type_text(text, interval)
                    display = text[:47] + "..." if len(text) > 50 else text
                    log(f"  Typed: {display}", "INFO")
                    return [TextContent(type="text", text=f"Typed: {display}")]

                elif name == "open_app":
                    app_name = arguments["app_name"]
                    delay = float(arguments.get("delay", 0.5))
                    self.mouse.open_app(app_name, delay)
                    log(f"  Opening: {app_name}", "INFO")
                    return [TextContent(type="text", text=f"Opened Spotlight and searched for: {app_name}")]

                # Accessibility API tools
                elif name == "check_accessibility_permissions":
                    if not ACCESSIBILITY_AVAILABLE:
                        return [TextContent(type="text", text="Accessibility API not available. Install atomacos: pip install atomacos")]
                    has_perms = self.accessibility.has_permissions() if self.accessibility else False
                    if has_perms:
                        log("  Accessibility: permissions granted", "INFO")
                        return [TextContent(type="text", text="Accessibility permissions are granted.")]
                    else:
                        log("  Accessibility: permissions NOT granted", "WARN")
                        return [TextContent(type="text", text="Accessibility permissions NOT granted. Enable in System Preferences > Privacy & Security > Accessibility")]

                elif name == "click_button":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    title = arguments.get("title")
                    title_contains = arguments.get("title_contains")
                    if not title and not title_contains:
                        return [TextContent(type="text", text="Error: Must specify 'title' or 'title_contains'")]
                    result = self.accessibility.click_button(
                        title=title, title_contains=title_contains,
                        in_focused_window=arguments.get("in_focused_window", True)
                    )
                    if result["success"]:
                        btn = result.get("button", {})
                        log(f"  Clicked button: {btn.get('title')}", "INFO")
                        return [TextContent(type="text", text=f"Clicked button: '{btn.get('title', 'unknown')}'")]
                    else:
                        log(f"  Button click failed: {result.get('error')}", "WARN")
                        return [TextContent(type="text", text=f"Failed: {result.get('error')}")]

                elif name == "find_buttons":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    buttons = self.accessibility.find_buttons(
                        title_contains=arguments.get("title_contains"),
                        in_focused_window=arguments.get("in_focused_window", True)
                    )
                    log(f"  Found {len(buttons)} buttons", "INFO")
                    if not buttons:
                        return [TextContent(type="text", text="No buttons found.")]
                    lines = [f"Found {len(buttons)} button(s):"]
                    for i, btn in enumerate(buttons[:30], 1):
                        title = btn.get("title") or "(no title)"
                        enabled = "enabled" if btn.get("enabled", True) else "disabled"
                        pos = btn.get("position", {})
                        pos_str = f"at ({pos.get('x', '?')}, {pos.get('y', '?')})" if pos else ""
                        lines.append(f"  {i}. \"{title}\" [{enabled}] {pos_str}")
                    return [TextContent(type="text", text="\n".join(lines))]

                elif name == "find_ui_elements":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    elements = self.accessibility.find_elements(
                        role=arguments.get("role"), title=arguments.get("title"),
                        title_contains=arguments.get("title_contains"),
                        in_focused_window=arguments.get("in_focused_window", True)
                    )
                    log(f"  Found {len(elements)} elements", "INFO")
                    if not elements:
                        return [TextContent(type="text", text="No elements found.")]
                    lines = [f"Found {len(elements)} element(s):"]
                    for i, elem in enumerate(elements[:30], 1):
                        role = elem.get("role", "?")
                        title = elem.get("title") or elem.get("description") or "(no title)"
                        pos = elem.get("position", {})
                        pos_str = f"at ({pos.get('x', '?')}, {pos.get('y', '?')})" if pos else ""
                        lines.append(f"  {i}. [{role}] \"{title}\" {pos_str}")
                    return [TextContent(type="text", text="\n".join(lines))]

                elif name == "click_ui_element":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    result = self.accessibility.click_element(
                        role=arguments["role"], title=arguments.get("title"),
                        title_contains=arguments.get("title_contains"),
                        in_focused_window=arguments.get("in_focused_window", True)
                    )
                    if result["success"]:
                        elem = result.get("element", {})
                        log(f"  Clicked: {elem.get('role')} - {elem.get('title')}", "INFO")
                        return [TextContent(type="text", text=f"Clicked {elem.get('role')}: '{elem.get('title', 'unknown')}'")]
                    else:
                        log(f"  Click failed: {result.get('error')}", "WARN")
                        return [TextContent(type="text", text=f"Failed: {result.get('error')}")]

                elif name == "click_menu_item":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    menu_path = arguments["menu_path"]
                    if not menu_path or not isinstance(menu_path, list):
                        return [TextContent(type="text", text="Error: menu_path must be a non-empty list")]
                    result = self.accessibility.click_menu_item(menu_path)
                    if result["success"]:
                        log(f"  Clicked menu: {' > '.join(menu_path)}", "INFO")
                        return [TextContent(type="text", text=f"Clicked menu: {' > '.join(menu_path)}")]
                    else:
                        log(f"  Menu click failed: {result.get('error')}", "WARN")
                        return [TextContent(type="text", text=f"Failed: {result.get('error')}")]

                elif name == "get_element_at_position":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    x, y = int(arguments["x"]), int(arguments["y"])
                    elem = self.accessibility.get_element_at_position(x, y)
                    if elem:
                        log(f"  Element at ({x}, {y}): {elem.get('role')}", "INFO")
                        lines = [f"Element at ({x}, {y}):", f"  Role: {elem.get('role', '?')}"]
                        if elem.get("title"): lines.append(f"  Title: {elem['title']}")
                        if elem.get("description"): lines.append(f"  Description: {elem['description']}")
                        if elem.get("position"): lines.append(f"  Position: ({elem['position']['x']}, {elem['position']['y']})")
                        if elem.get("size"): lines.append(f"  Size: {elem['size']['width']}x{elem['size']['height']}")
                        return [TextContent(type="text", text="\n".join(lines))]
                    else:
                        return [TextContent(type="text", text=f"No element at ({x}, {y})")]

                elif name == "get_focused_window_info":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    app = self.accessibility.get_focused_application()
                    window = self.accessibility.get_focused_window()
                    lines = ["Focused Application and Window:"]
                    if app:
                        lines.append(f"\nApplication: {app.get('title', 'unknown')}")
                    if window:
                        _, w = window
                        lines.append(f"\nWindow: {w.get('title', 'unknown')}")
                        if w.get("position"): lines.append(f"  Position: ({w['position']['x']}, {w['position']['y']})")
                        if w.get("size"): lines.append(f"  Size: {w['size']['width']}x{w['size']['height']}")
                    log(f"  Focused: {app.get('title') if app else 'none'}", "INFO")
                    return [TextContent(type="text", text="\n".join(lines))]

                elif name == "get_ui_tree":
                    if not self.accessibility:
                        return [TextContent(type="text", text="Accessibility API not available.")]
                    max_depth = min(int(arguments.get("max_depth", 3)), 10)
                    tree = self.accessibility.get_ui_tree(
                        in_focused_window=arguments.get("in_focused_window", True),
                        max_depth=max_depth
                    )
                    if not tree:
                        return [TextContent(type="text", text="No UI tree available")]

                    def fmt(node: dict, indent: int = 0) -> List[str]:
                        lines = []
                        role = node.get("role", "?")
                        title = node.get("title") or node.get("description") or ""
                        lines.append("  " * indent + f"[{role}]" + (f' "{title}"' if title else ""))
                        for child in node.get("children", [])[:20]:
                            lines.extend(fmt(child, indent + 1))
                        return lines

                    output = ["UI Element Tree:"]
                    for root in tree:
                        output.extend(fmt(root))
                    log(f"  UI tree: depth={max_depth}", "INFO")
                    return [TextContent(type="text", text="\n".join(output[:200]))]

                else:
                    log(f"  Unknown tool: {name}", "WARN")
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except ValueError as e:
                log(f"  Error: {e}", "ERROR")
                return [TextContent(type="text", text=f"Error: {e}")]
            except Exception as e:
                log(f"  Unexpected error: {e}", "ERROR")
                return [TextContent(type="text", text=f"Unexpected error: {e}")]

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
