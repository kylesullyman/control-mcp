"""MCP server for mouse control."""

import asyncio
import sys
from typing import Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .mouse_control import MouseController
from .log_window import start_log_window, log
from .config import load_settings
from .tools import get_tool_definitions


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
            return get_tool_definitions()


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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    # Default to half screen dimensions for ~2x2 pixel cells
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
                    default_rows = self.mouse.screen_height // 2
                    default_cols = self.mouse.screen_width // 2
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
