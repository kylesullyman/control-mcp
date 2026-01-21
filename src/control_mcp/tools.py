"""Tool definitions for MCP server."""

from mcp.types import Tool


def get_tool_definitions() -> list[Tool]:
    """Return list of available mouse control tools."""
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
                        "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/2.",
                    },
                    "cols": {
                        "type": "number",
                        "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/2.",
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
            description="Take a screenshot with a labeled grid overlay for precise targeting. ALWAYS use this BEFORE clicking to locate UI elements. The screen is divided into a fine grid (default: rows=screen_height/2, cols=screen_width/2, creating ~2x2 pixel cells). Cells are labeled like a spreadsheet: columns A-Z (then AA, AB...), rows 1-N. Cell 'A1' is top-left. After examining the grid, use click_grid_cell to click the cell containing your target.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "number",
                        "description": "Number of rows in the grid. Default is screen_height/2 for ~2px tall cells.",
                    },
                    "cols": {
                        "type": "number",
                        "description": "Number of columns in the grid. Default is screen_width/2 for ~2px wide cells.",
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
                        "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/2.",
                    },
                    "cols": {
                        "type": "number",
                        "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/2.",
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
                        "description": "Number of rows in the grid (must match screenshot_with_grid). Default is screen_height/2.",
                    },
                    "cols": {
                        "type": "number",
                        "description": "Number of columns in the grid (must match screenshot_with_grid). Default is screen_width/2.",
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
                        "description": "Grid rows for precision. Default is screen_height/2.",
                    },
                    "cols": {
                        "type": "number",
                        "description": "Grid columns for precision. Default is screen_width/2.",
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
                        "description": "Rows in the parent grid (must match previous screenshot). Default is screen_height/2.",
                    },
                    "parent_cols": {
                        "type": "number",
                        "description": "Columns in the parent grid (must match previous screenshot). Default is screen_width/2.",
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
                        "description": "Rows in the parent grid. Default is screen_height/2.",
                    },
                    "parent_cols": {
                        "type": "number",
                        "description": "Columns in the parent grid. Default is screen_width/2.",
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

