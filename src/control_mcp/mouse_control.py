"""Mouse control functionality using pyautogui."""

import pyautogui
import base64
import io
import time
import random
from typing import Tuple, Optional, Literal, List

# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small delay between actions


def _cubic_bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """
    Calculate a point on a cubic bezier curve.

    Args:
        t: Parameter from 0 to 1
        p0, p1, p2, p3: Control points

    Returns:
        The interpolated value at parameter t
    """
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t ** 2 * p2
        + t ** 3 * p3
    )


def _generate_bezier_path(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    num_points: int = 50,
    curvature: float = 0.5,
) -> List[Tuple[int, int]]:
    """
    Generate points along a cubic bezier curve between two positions.

    Args:
        start_x, start_y: Starting coordinates
        end_x, end_y: Ending coordinates
        num_points: Number of points to generate along the curve
        curvature: How much the curve deviates (0 = straight, 1 = very curved)

    Returns:
        List of (x, y) coordinate tuples along the bezier curve
    """
    # Calculate the distance between points
    dx = end_x - start_x
    dy = end_y - start_y
    distance = (dx ** 2 + dy ** 2) ** 0.5

    # Generate control points with some randomness for natural movement
    # Control points are offset perpendicular to the line between start and end
    offset_scale = distance * curvature * random.uniform(0.3, 0.7)

    # Random direction for the curve (above or below the direct line)
    direction = random.choice([-1, 1])

    # Perpendicular vector (normalized)
    if distance > 0:
        perp_x = -dy / distance
        perp_y = dx / distance
    else:
        perp_x, perp_y = 0, 0

    # First control point: 1/3 of the way, offset perpendicular
    cp1_x = start_x + dx * 0.3 + perp_x * offset_scale * direction
    cp1_y = start_y + dy * 0.3 + perp_y * offset_scale * direction

    # Second control point: 2/3 of the way, offset perpendicular (same direction)
    cp2_x = start_x + dx * 0.7 + perp_x * offset_scale * direction * random.uniform(0.5, 1.0)
    cp2_y = start_y + dy * 0.7 + perp_y * offset_scale * direction * random.uniform(0.5, 1.0)

    # Generate points along the curve
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = int(_cubic_bezier(t, start_x, cp1_x, cp2_x, end_x))
        y = int(_cubic_bezier(t, start_y, cp1_y, cp2_y, end_y))
        points.append((x, y))

    return points


class MouseController:
    """Handles low-level mouse control operations."""

    def __init__(self):
        """Initialize the mouse controller."""
        self.screen_width, self.screen_height = pyautogui.size()

    def get_cursor_position(self) -> Tuple[int, int]:
        """
        Get the current cursor position.

        Returns:
            Tuple of (x, y) coordinates
        """
        x, y = pyautogui.position()
        return (x, y)

    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get the screen dimensions (returns cached values from initialization).

        Returns:
            Tuple of (width, height)
        """
        return (self.screen_width, self.screen_height)

    def _refresh_screen_size(self) -> None:
        """Refresh stored screen dimensions from the system."""
        self.screen_width, self.screen_height = pyautogui.size()

    def validate_coordinates(self, x: int, y: int) -> bool:
        """
        Check if coordinates are within screen bounds.
        Refreshes screen size before validation.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if coordinates are valid, False otherwise
        """
        self._refresh_screen_size()
        return 0 <= x < self.screen_width and 0 <= y < self.screen_height

    def _move_along_bezier(
        self, end_x: int, end_y: int, duration: float = 0.3, curvature: float = 0.3
    ) -> None:
        """
        Move the cursor along a bezier curve to the target position.

        Args:
            end_x: Target X coordinate
            end_y: Target Y coordinate
            duration: Total time for the movement in seconds
            curvature: How curved the path should be (0 = straight, 1 = very curved)
        """
        start_x, start_y = pyautogui.position()

        # For very short movements, just move directly
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance < 10:
            pyautogui.moveTo(end_x, end_y, duration=duration)
            return

        # Calculate number of points based on distance and duration
        num_points = max(10, min(100, int(distance / 5)))

        # Generate the bezier path
        points = _generate_bezier_path(
            start_x, start_y, end_x, end_y, num_points=num_points, curvature=curvature
        )

        # Calculate delay between points
        delay = duration / len(points) if points else 0

        # Temporarily disable pyautogui's pause for smoother movement
        original_pause = pyautogui.PAUSE
        pyautogui.PAUSE = 0

        try:
            # Move through each point
            for point_x, point_y in points[1:]:  # Skip first point (current position)
                pyautogui.moveTo(point_x, point_y, duration=0)
                time.sleep(delay)

            # Ensure we end up exactly at the target
            pyautogui.moveTo(end_x, end_y, duration=0)
        finally:
            pyautogui.PAUSE = original_pause

    def _drag_along_bezier(
        self,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: Literal["left", "right", "middle"] = "left",
        curvature: float = 0.3,
    ) -> None:
        """
        Drag the cursor along a bezier curve to the target position.

        Args:
            end_x: Target X coordinate
            end_y: Target Y coordinate
            duration: Total time for the drag in seconds
            button: Mouse button to hold during drag
            curvature: How curved the path should be (0 = straight, 1 = very curved)
        """
        start_x, start_y = pyautogui.position()

        # For very short movements, just drag directly
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance < 10:
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            return

        # Calculate number of points based on distance and duration
        num_points = max(10, min(100, int(distance / 5)))

        # Generate the bezier path
        points = _generate_bezier_path(
            start_x, start_y, end_x, end_y, num_points=num_points, curvature=curvature
        )

        # Calculate delay between points
        delay = duration / len(points) if points else 0

        # Temporarily disable pyautogui's pause for smoother movement
        original_pause = pyautogui.PAUSE
        pyautogui.PAUSE = 0

        try:
            # Press mouse button down
            pyautogui.mouseDown(button=button)

            # Move through each point
            for point_x, point_y in points[1:]:  # Skip first point (current position)
                pyautogui.moveTo(point_x, point_y, duration=0)
                time.sleep(delay)

            # Ensure we end up exactly at the target
            pyautogui.moveTo(end_x, end_y, duration=0)

            # Release mouse button
            pyautogui.mouseUp(button=button)
        finally:
            pyautogui.PAUSE = original_pause

    def move_cursor(self, x: int, y: int, duration: float = 0.3) -> None:
        """
        Move the cursor to specified coordinates along a bezier curve.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Time in seconds for smooth movement (default: 0.3)

        Raises:
            ValueError: If coordinates are outside screen bounds
        """
        if not self.validate_coordinates(x, y):
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside screen bounds "
                f"(0-{self.screen_width}, 0-{self.screen_height})"
            )

        self._move_along_bezier(x, y, duration=duration)

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: Literal["left", "right", "middle"] = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> None:
        """
        Perform mouse click(s) at specified or current position.

        Args:
            x: X coordinate (None for current position)
            y: Y coordinate (None for current position)
            button: Mouse button to click ("left", "right", or "middle")
            clicks: Number of clicks
            interval: Time between clicks in seconds

        Raises:
            ValueError: If coordinates are outside screen bounds or button is invalid
        """
        if button not in ["left", "right", "middle"]:
            raise ValueError(f"Invalid button: {button}. Must be 'left', 'right', or 'middle'")

        if x is not None and y is not None:
            if not self.validate_coordinates(x, y):
                raise ValueError(
                    f"Coordinates ({x}, {y}) are outside screen bounds "
                    f"(0-{self.screen_width}, 0-{self.screen_height})"
                )
            # Move to position with bezier curve animation first
            self._move_along_bezier(x, y, duration=0.3)
            # Then click at the current position
            pyautogui.click(clicks=clicks, interval=interval, button=button)
        else:
            pyautogui.click(clicks=clicks, interval=interval, button=button)

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
        button: Literal["left", "right", "middle"] = "left",
    ) -> None:
        """
        Drag from one position to another.

        Args:
            from_x: Starting X coordinate
            from_y: Starting Y coordinate
            to_x: Ending X coordinate
            to_y: Ending Y coordinate
            duration: Time for drag operation in seconds
            button: Mouse button to use for dragging

        Raises:
            ValueError: If coordinates are outside screen bounds or button is invalid
        """
        if button not in ["left", "right", "middle"]:
            raise ValueError(f"Invalid button: {button}. Must be 'left', 'right', or 'middle'")

        if not self.validate_coordinates(from_x, from_y):
            raise ValueError(
                f"Start coordinates ({from_x}, {from_y}) are outside screen bounds "
                f"(0-{self.screen_width}, 0-{self.screen_height})"
            )

        if not self.validate_coordinates(to_x, to_y):
            raise ValueError(
                f"End coordinates ({to_x}, {to_y}) are outside screen bounds "
                f"(0-{self.screen_width}, 0-{self.screen_height})"
            )

        # Move to start position first with bezier curve
        self._move_along_bezier(from_x, from_y, duration=0.3)
        # Perform drag along bezier curve
        self._drag_along_bezier(to_x, to_y, duration=duration, button=button)

    def scroll(
        self, amount: int, x: Optional[int] = None, y: Optional[int] = None
    ) -> None:
        """
        Scroll at the current or specified cursor position.

        Args:
            amount: Scroll amount (positive = up, negative = down)
            x: X coordinate to scroll at (None for current position)
            y: Y coordinate to scroll at (None for current position)

        Raises:
            ValueError: If coordinates are outside screen bounds
        """
        if x is not None and y is not None:
            if not self.validate_coordinates(x, y):
                raise ValueError(
                    f"Coordinates ({x}, {y}) are outside screen bounds "
                    f"(0-{self.screen_width}, 0-{self.screen_height})"
                )
            self._move_along_bezier(x, y, duration=0.3)

        pyautogui.scroll(amount)

    def screenshot(self) -> str:
        """
        Take a full screen screenshot.

        Returns:
            Base64-encoded PNG image as a string
        """
        image = pyautogui.screenshot()

        # Convert image to base64-encoded PNG
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return image_base64

    def keyboard_shortcut(self, *keys: str) -> None:
        """
        Send a keyboard shortcut (hotkey combination).

        Args:
            *keys: Keys to press together (e.g., "command", "c" for Cmd+C)

        Common modifier keys for macOS:
            - "command" or "cmd" - Command key
            - "option" or "alt" - Option key
            - "control" or "ctrl" - Control key
            - "shift" - Shift key

        Examples:
            keyboard_shortcut("command", "c")  # Copy
            keyboard_shortcut("command", "v")  # Paste
            keyboard_shortcut("command", "shift", "4")  # Screenshot selection
        """
        if not keys:
            raise ValueError("At least one key must be provided")
        pyautogui.hotkey(*keys)

    def key_press(self, key: str, presses: int = 1, interval: float = 0.1) -> None:
        """
        Press a single key one or more times.

        Args:
            key: The key to press (e.g., "enter", "escape", "tab", "a")
            presses: Number of times to press the key
            interval: Time between presses in seconds
        """
        pyautogui.press(key, presses=presses, interval=interval)

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """
        Type text character by character.

        Args:
            text: The text to type
            interval: Time between keystrokes in seconds

        Note:
            This uses pyautogui.write() which works with ASCII characters.
            For Unicode characters, use keyboard_shortcut to paste from clipboard.
        """
        pyautogui.write(text, interval=interval)

    def open_app(self, app_name: str, delay: float = 0.5) -> None:
        """
        Open an application using Spotlight search (Command+Space).

        Args:
            app_name: The name of the application to open (e.g., "Safari", "Terminal")
            delay: Time to wait for Spotlight to appear before typing (default: 0.5s, max: 1.0s)

        This method:
        1. Opens Spotlight with Command+Space
        2. Waits for Spotlight to appear
        3. Types the app name
        4. Presses Enter to launch the app
        """
        # Open Spotlight
        pyautogui.hotkey("command", "space")

        # Wait for Spotlight to appear (cap at 1 second max)
        time.sleep(min(delay, 1.0))

        # Type the app name
        pyautogui.write(app_name, interval=0.02)

        # Small delay before pressing Enter
        time.sleep(0.1)

        # Press Enter to launch
        pyautogui.press("enter")
