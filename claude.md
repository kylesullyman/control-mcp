# Mouse Control MCP Server

## Overview
Build an MCP (Model Context Protocol) server that provides low-level mouse control capabilities on macOS using Python. This server will allow direct cursor positioning and clicking rather than relying on application-specific APIs.

## Goals
- Get current cursor position on screen
- Move cursor to specific coordinates
- Perform mouse clicks (left, right, double-click)
- Perform drag operations
- Work at the OS level without requiring app-specific APIs

## Technical Approach

### Technology Stack
- **Language**: Python 3.x
- **Mouse Control Library**: `pyautogui` or `pynput`
  - `pyautogui`: Higher-level API with built-in safety features
  - `pynput`: Lower-level control with better performance
- **MCP SDK**: Use the official MCP Python SDK
- **Platform**: macOS-specific (requires Accessibility permissions)

### Required Python Packages
```
mcp
pyautogui  # or pynput
```

### MCP Tools to Implement

#### 1. `get_cursor_position`
- Returns current (x, y) coordinates of the cursor
- No parameters required
- Response: `{"x": int, "y": int}`

#### 2. `move_cursor`
- Moves cursor to specified coordinates
- Parameters:
  - `x`: int - X coordinate
  - `y`: int - Y coordinate
  - `duration`: float (optional) - Time in seconds for smooth movement (default: 0)
- Response: Success confirmation

#### 3. `click`
- Performs a mouse click at current position or specified coordinates
- Parameters:
  - `x`: int (optional) - X coordinate (clicks current position if not provided)
  - `y`: int (optional) - Y coordinate
  - `button`: string - "left", "right", or "middle" (default: "left")
  - `clicks`: int - Number of clicks (default: 1)
  - `interval`: float - Time between clicks in seconds (default: 0.1)
- Response: Success confirmation

#### 4. `drag`
- Drags from one position to another
- Parameters:
  - `from_x`: int - Starting X coordinate
  - `from_y`: int - Starting Y coordinate
  - `to_x`: int - Ending X coordinate
  - `to_y`: int - Ending Y coordinate
  - `duration`: float - Time for drag operation (default: 0.5)
  - `button`: string - "left", "right", or "middle" (default: "left")
- Response: Success confirmation

#### 5. `scroll`
- Scrolls at the current cursor position
- Parameters:
  - `x`: int (optional) - X coordinate to scroll at
  - `y`: int (optional) - Y coordinate to scroll at
  - `amount`: int - Scroll amount (positive = up, negative = down)
- Response: Success confirmation

#### 6. `get_screen_size`
- Returns the screen dimensions
- No parameters required
- Response: `{"width": int, "height": int}`

## Implementation Structure

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

## Key Implementation Details

### Permissions
On macOS, the application will need Accessibility permissions:
- User must grant permission in System Preferences > Security & Privacy > Privacy > Accessibility
- The server should provide clear error messages if permissions are not granted

### Safety Features
- Add bounds checking to prevent cursor from going off-screen
- Optional safety feature: Prevent clicks in dangerous areas (configurable)
- Add small delays between rapid operations to prevent issues

### Error Handling
- Handle permission errors gracefully
- Validate coordinate ranges
- Catch and report mouse control failures

## Example Usage

Once implemented, Claude could use it like this:

```python
# Get current cursor position
position = get_cursor_position()
# Returns: {"x": 500, "y": 300}

# Move cursor to specific location
move_cursor(x=100, y=200, duration=0.5)

# Click at current position
click(button="left", clicks=1)

# Click at specific coordinates
click(x=150, y=250, button="left")

# Drag operation
drag(from_x=100, from_y=100, to_x=300, to_y=300, duration=1.0)

# Scroll
scroll(x=500, y=500, amount=5)

# Get screen dimensions
screen = get_screen_size()
# Returns: {"width": 1920, "height": 1080}
```

## Testing Strategy
1. Test basic cursor movement
2. Test clicking at various screen positions
3. Test drag operations
4. Verify permission handling
5. Test edge cases (coordinates outside screen bounds)

## Development Workflow

### Version Control for Parallel Claude Instances

**IMPORTANT**: Multiple Claude instances may work on this codebase simultaneously. Follow these rules to avoid conflicts:

#### Before Starting ANY Work
1. **Sync with remote first**:
   ```bash
   git fetch origin
   git status
   ```
2. **Check for other active branches**: `git branch -a` - See what others are working on
3. **Review uncommitted changes**: `git status` and `git diff`

#### Branch Strategy for Parallel Work
1. **Always create a unique branch immediately**:
   ```bash
   # Use descriptive names with timestamp or session ID
   git checkout -b feature/tool-name-YYYYMMDD-HHMM
   # Example: feature/scroll-tool-20260115-1430
   ```
2. **Never work directly on main** - Each Claude instance must use its own branch
3. **One branch per task** - Keep branches focused and short-lived
4. **Branch naming conventions**:
   - `feature/description-timestamp` - New features
   - `fix/description-timestamp` - Bug fixes
   - `refactor/description-timestamp` - Code improvements

#### During Development
1. **Commit frequently and atomically**:
   ```bash
   git add <specific-files>
   git commit -m "Descriptive message about the change"
   ```
2. **Push to remote immediately after each commit**:
   ```bash
   git push -u origin <branch-name>
   ```
3. **Sync with main regularly** to avoid divergence:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
4. **Keep commits atomic**: Each commit should represent a single logical change

#### Avoiding Conflicts
- **Check git status before and after every operation**
- **Coordinate through branch names**: Descriptive branches show what's being worked on
- **Avoid modifying the same files**: Check active branches to see what files others are touching
- **If you see unstaged changes from another instance**:
  - Commit them first, or
  - Stash them: `git stash`, then apply later: `git stash pop`

#### Merging Your Work
1. **Ensure your branch is up to date**:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. **Push your final changes**:
   ```bash
   git push origin <branch-name>
   ```
3. **The user will handle merging to main** or let them know the branch is ready

### Making Changes
- **Pull/fetch before every session**
- **Branch immediately** - Never work on main with parallel instances
- Write clear commit messages that explain the "why" not just the "what"
- **Commit and push after each logical change** - Don't batch commits
- **Small, frequent commits are better** than large infrequent ones
- Test changes locally before committing
- **State your branch name when starting work** so the user can track parallel efforts

## Next Steps
1. Set up Python project structure with pyproject.toml
2. Install MCP SDK and mouse control library
3. Implement MCP server with basic tools
4. Add error handling and safety features
5. Test with Claude Desktop
6. Document setup and usage in README.md
