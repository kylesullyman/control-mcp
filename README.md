# Control MCP - Mouse Control Server

A Model Context Protocol (MCP) server that provides low-level mouse control capabilities on macOS. This server allows you to control the cursor position, perform clicks, drag operations, scroll, and take screenshots using Python's pyautogui library.

## Features

- **Get Cursor Position**: Retrieve current mouse coordinates
- **Move Cursor**: Move to specific screen coordinates with optional smooth movement
- **Click**: Perform left, right, or middle clicks at any position (single or multiple clicks)
- **Drag**: Drag from one position to another
- **Scroll**: Scroll up or down at any position
- **Get Screen Size**: Get screen dimensions
- **Screenshot**: Capture the entire screen or a specific region as a PNG image

## Installation

1. **Install dependencies**:
   ```bash
   cd /Users/kylesullivan/Documents/coding_projects/control-mcp
   pip install -e .
   ```

2. **Grant Accessibility Permissions**:
   - Go to **System Preferences > Security & Privacy > Privacy > Accessibility**
   - Add and enable the terminal application or Python executable you're using
   - This is required for the mouse control to work on macOS

## Configuration

Add this MCP server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "control-mcp": {
      "command": "python3",
      "args": [
        "-m",
        "control_mcp.server"
      ]
    }
  }
}
```

After updating the config, restart Claude Desktop.

## Available Tools

### 1. get_cursor_position
Get the current cursor position on screen.

**Parameters**: None

**Example**:
```
Use get_cursor_position to find where my mouse is
```

### 2. move_cursor
Move the cursor to specified coordinates.

**Parameters**:
- `x` (number, required): X coordinate in pixels from left
- `y` (number, required): Y coordinate in pixels from top
- `duration` (number, optional): Duration of movement in seconds (0 for instant, default: 0)

**Example**:
```
Move the cursor to position x=500, y=300 with a smooth 1 second movement
```

### 3. click
Perform mouse click at current position or specified coordinates.

**Parameters**:
- `x` (number, optional): X coordinate
- `y` (number, optional): Y coordinate
- `button` (string, optional): "left", "right", or "middle" (default: "left")
- `clicks` (number, optional): Number of clicks, use 2 for double-click (default: 1)
- `interval` (number, optional): Time between clicks in seconds (default: 0.1)

**Examples**:
```
Click at position x=100, y=200
Double-click at x=300, y=400
Right-click at the current cursor position
```

### 4. drag
Drag from one position to another.

**Parameters**:
- `from_x` (number, required): Starting X coordinate
- `from_y` (number, required): Starting Y coordinate
- `to_x` (number, required): Ending X coordinate
- `to_y` (number, required): Ending Y coordinate
- `duration` (number, optional): Duration of drag in seconds (default: 0.5)
- `button` (string, optional): "left", "right", or "middle" (default: "left")

**Example**:
```
Drag from position (100, 100) to (300, 300) over 1 second
```

### 5. scroll
Scroll at current or specified cursor position.

**Parameters**:
- `amount` (number, required): Scroll amount (positive = up, negative = down)
- `x` (number, optional): X coordinate to scroll at
- `y` (number, optional): Y coordinate to scroll at

**Example**:
```
Scroll up by 5 clicks at position x=500, y=500
Scroll down by 10 clicks at the current position
```

### 6. get_screen_size
Get the screen dimensions.

**Parameters**: None

**Example**:
```
What is my screen size?
```

### 7. screenshot
Capture the entire screen or a specific region as a PNG image.

**Parameters**:
- `region` (array, optional): Region to capture as `[x, y, width, height]`
  - `x`: X coordinate of the top-left corner
  - `y`: Y coordinate of the top-left corner
  - `width`: Width of the region in pixels
  - `height`: Height of the region in pixels
  - If not provided, captures the entire screen

**Examples**:
```
Take a screenshot of the entire screen
Take a screenshot of the region starting at (100, 100) with width 800 and height 600
```

**Returns**: A PNG image in base64 format that Claude can display

## Safety Features

- **FAILSAFE**: Move mouse to any corner of the screen to abort operations
- **Bounds Checking**: All coordinates are validated against screen dimensions
- **Error Handling**: Clear error messages for invalid inputs
- **Pause Between Actions**: Small delay (0.1s) between operations to prevent issues

## How Claude Decides to Use These Tools

Claude automatically chooses to use these tools based on your request. The tool descriptions contain keywords that help Claude recognize when to use them. Here are phrases that will trigger Claude to use the mouse control tools:

### Trigger Phrases (Claude will recognize these)

| What You Say | Tools Claude Will Use |
|--------------|----------------------|
| "Click on the button" | `screenshot` → `click` |
| "Show me what's on my screen" | `screenshot` |
| "Where is my mouse?" | `get_cursor_position` |
| "Move the cursor to..." | `move_cursor` |
| "Scroll down the page" | `scroll` |
| "Drag this file to..." | `drag` |
| "Open that app" (with screenshot) | `screenshot` → `move_cursor` → `click` (double) |
| "What's my screen resolution?" | `get_screen_size` |

### Tips for Better Results

1. **Ask Claude to look first**: "Take a screenshot and click the Settings button"
2. **Be specific about actions**: "Double-click" vs "click", "right-click" for context menus
3. **Reference UI elements**: "Click the blue Submit button" helps Claude find it in screenshots
4. **Chain actions**: "Take a screenshot, find the search box, and click on it"

## Usage Examples

Once configured in Claude Desktop, you can ask Claude to control your mouse:

1. **See your screen**:
   ```
   Take a screenshot and tell me what apps are open
   ```

2. **Click on something**:
   ```
   Take a screenshot and click on the Safari icon in the dock
   ```

3. **Find cursor position**:
   ```
   Where is my mouse cursor right now?
   ```

4. **Move and click**:
   ```
   Move the cursor to x=200, y=300 and click
   ```

5. **Double-click to open**:
   ```
   Double-click at position x=150, y=250
   ```

6. **Drag operation**:
   ```
   Drag from (100, 100) to (500, 500)
   ```

7. **Scroll a page**:
   ```
   Scroll down 10 clicks on the current page
   ```

8. **Complex task**:
   ```
   Take a screenshot, find the Chrome browser, and open it
   ```

## Troubleshooting

### Permission Errors
If you get permission errors:
1. Check that Accessibility permissions are granted
2. Restart Claude Desktop after granting permissions
3. Make sure you've granted permissions to the correct application (Terminal, Python, etc.)

### Coordinates Outside Bounds
If clicks or movements fail:
1. Use `get_screen_size` to check your screen dimensions
2. Ensure coordinates are within `0` to `screen_width-1` and `0` to `screen_height-1`

### Module Not Found
If you get import errors:
1. Make sure you ran `pip install -e .` from the project directory
2. Verify the `cwd` path in your Claude Desktop config points to the `src` directory

## Development

### Project Structure
```
control-mcp/
├── src/
│   └── control_mcp/
│       ├── __init__.py
│       ├── server.py          # Main MCP server
│       └── mouse_control.py   # Mouse control logic
├── pyproject.toml
├── README.md
└── claude.md
```

### Testing Manually
You can test the mouse controller directly:

```python
from control_mcp.mouse_control import MouseController

mouse = MouseController()

# Get position
x, y = mouse.get_cursor_position()
print(f"Cursor at: {x}, {y}")

# Move cursor
mouse.move_cursor(500, 300)

# Click
mouse.click(100, 200)

# Take a screenshot
image_base64 = mouse.screenshot()
print(f"Screenshot taken, {len(image_base64)} bytes")

# Screenshot a specific region
region_image = mouse.screenshot(region=(100, 100, 800, 600))
print(f"Region screenshot taken")
```

## License

MIT License

## Notes

- This tool provides direct mouse control at the OS level
- Use responsibly and be aware of where you're clicking
- The FAILSAFE feature allows you to abort by moving mouse to screen corners
