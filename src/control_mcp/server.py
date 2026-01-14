"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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
                    description="Get the current cursor position on screen",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="move_cursor",
                    description="Move the cursor to specified screen coordinates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate (pixels from left)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate (pixels from top)",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Duration of movement in seconds (0 for instant)",
                                "default": 0.0,
                            },
                        },
                        "required": ["x", "y"],
                    },
                ),
                Tool(
                    name="click",
                    description="Perform mouse click at current position or specified coordinates",
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
                                "description": "Number of clicks (for double-click, use 2)",
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
                    description="Drag from one position to another",
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
                    description="Scroll at current or specified cursor position",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Scroll amount (positive = up, negative = down)",
                            },
                            "x": {
                                "type": "number",
                                "description": "X coordinate to scroll at (optional, uses current position if not provided)",
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to scroll at (optional, uses current position if not provided)",
                            },
                        },
                        "required": ["amount"],
                    },
                ),
                Tool(
                    name="get_screen_size",
                    description="Get the screen dimensions (width and height)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
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
