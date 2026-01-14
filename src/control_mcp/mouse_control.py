"""Mouse control functionality using pyautogui."""

import pyautogui
from typing import Tuple, Optional, Literal

# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small delay between actions


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
        Get the screen dimensions.

        Returns:
            Tuple of (width, height)
        """
        return (self.screen_width, self.screen_height)

    def validate_coordinates(self, x: int, y: int) -> bool:
        """
        Check if coordinates are within screen bounds.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if coordinates are valid, False otherwise
        """
        return 0 <= x < self.screen_width and 0 <= y < self.screen_height

    def move_cursor(self, x: int, y: int, duration: float = 0.0) -> None:
        """
        Move the cursor to specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Time in seconds for smooth movement (0 for instant)

        Raises:
            ValueError: If coordinates are outside screen bounds
        """
        if not self.validate_coordinates(x, y):
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside screen bounds "
                f"(0-{self.screen_width}, 0-{self.screen_height})"
            )

        pyautogui.moveTo(x, y, duration=duration)

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
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
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

        # Move to start position first
        pyautogui.moveTo(from_x, from_y)
        # Perform drag
        pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration, button=button)

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
            pyautogui.moveTo(x, y)

        pyautogui.scroll(amount)
