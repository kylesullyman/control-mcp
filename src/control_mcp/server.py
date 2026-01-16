"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .mouse_control import MouseController


class MouseControlServer:
    """MCP server that provides mouse control tools."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("control-mcp")
        self.mouse = MouseController()
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
                    description="Move the mouse cursor to specific screen coordinates. Use this to navigate to buttons, menus, icons, or any UI element on the user's screen. Supports smooth animated movement with duration parameter.",
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
                                "description": "Duration of movement in seconds (0 for instant, use 0.5-1.0 for visible smooth movement)",
                                "default": 0.0,
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
                    description="Take a screenshot to see what's currently on the user's screen. Use this to see the current state of the desktop, find UI elements, verify actions completed successfully, or help the user with anything visual on their screen. Can capture full screen or a specific region.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "array",
                                "minItems": 4,
                                "maxItems": 4,
                                "items": {"type": "number"},
                                "description": "Optional region to capture as [x, y, width, height]. Omit to capture entire screen.",
                            },
                        },
                        "required": [],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[Union[TextContent, ImageContent]]:
            """Handle tool calls."""
            try:
                if name == "get_cursor_position":
                    x, y = self.mouse.get_cursor_position()
                    return [
                        TextContent(
                            type="text",
                            text=f"Current cursor position: x={x}, y={y}",
                        )
                    ]

                elif name == "move_cursor":
                    x = int(arguments["x"])
                    y = int(arguments["y"])
                    duration = float(arguments.get("duration", 0.0))
                    self.mouse.move_cursor(x, y, duration)
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
                    return [
                        TextContent(
                            type="text",
                            text=f"Scrolled {direction} by {abs(amount)} {position_str}",
                        )
                    ]

                elif name == "get_screen_size":
                    width, height = self.mouse.get_screen_size()
                    return [
                        TextContent(
                            type="text",
                            text=f"Screen size: width={width}, height={height}",
                        )
                    ]

                elif name == "screenshot":
                    region = None
                    if "region" in arguments:
                        region_list = arguments["region"]
                        region = tuple(int(v) for v in region_list)

                    image_base64 = self.mouse.screenshot(region)
                    region_str = f"region {region}" if region else "entire screen"
                    return [
                        TextContent(
                            type="text",
                            text=f"Screenshot of {region_str}:",
                        ),
                        ImageContent(
                            type="image",
                            data=image_base64,
                            mimeType="image/png",
                        ),
                    ]

                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown tool: {name}",
                        )
                    ]

            except ValueError as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Unexpected error: {str(e)}",
                    )
                ]

    async def run(self):
        """Run the server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main():
    """Main entry point."""
    server = MouseControlServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
