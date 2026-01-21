"""Mouse control functionality using pyautogui."""

import pyautogui
import base64
import io
import time
from typing import Tuple, Optional, Literal, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from .bezier_utils import generate_bezier_path

# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Small delay between actions


class MouseController:
    """Handles low-level mouse control operations."""

    def __init__(self, pixels_per_second: float = 2000.0, use_bezier: bool = True):
        """Initialize the mouse controller.

        Args:
            pixels_per_second: Speed of cursor movement (default: 2000.0)
                Higher values = faster movement
                Lower values = slower movement
            use_bezier: If True, use curved bezier paths for movement.
                If False, use straight line movement (default: True)
        """
        self.screen_width, self.screen_height = pyautogui.size()
        self.pixels_per_second = pixels_per_second
        self.use_bezier = use_bezier

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

    def _calculate_duration(self, start_x: int, start_y: int, end_x: int, end_y: int) -> float:
        """
        Calculate movement duration based on distance and speed.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate

        Returns:
            Duration in seconds based on distance and pixels_per_second
        """
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        duration = distance / self.pixels_per_second
        # Set minimum duration to avoid instant jumps
        return max(0.05, duration)

    def _move_along_bezier(
        self, end_x: int, end_y: int, duration: float = 0.1, curvature: float = 0.3
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
        points = generate_bezier_path(
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
        points = generate_bezier_path(
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

    def move_cursor(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """
        Move the cursor to specified coordinates.
        Movement speed is automatically calculated based on distance.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Optional override for movement duration in seconds.
                     If not provided, duration is calculated based on distance.

        Raises:
            ValueError: If coordinates are outside screen bounds
        """
        if not self.validate_coordinates(x, y):
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside screen bounds "
                f"(0-{self.screen_width}, 0-{self.screen_height})"
            )

        # Calculate duration based on distance if not provided
        if duration is None:
            current_x, current_y = pyautogui.position()
            duration = self._calculate_duration(current_x, current_y, x, y)

        if self.use_bezier:
            self._move_along_bezier(x, y, duration=duration)
        else:
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
            # Calculate duration based on distance
            current_x, current_y = pyautogui.position()
            duration = self._calculate_duration(current_x, current_y, x, y)
            # Move to position first
            if self.use_bezier:
                self._move_along_bezier(x, y, duration=duration)
            else:
                pyautogui.moveTo(x, y, duration=duration)
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

        # Calculate duration for initial movement based on distance
        current_x, current_y = pyautogui.position()
        move_duration = self._calculate_duration(current_x, current_y, from_x, from_y)
        # Move to start position first
        if self.use_bezier:
            self._move_along_bezier(from_x, from_y, duration=move_duration)
        else:
            pyautogui.moveTo(from_x, from_y, duration=move_duration)

        # Perform drag
        if self.use_bezier:
            self._drag_along_bezier(to_x, to_y, duration=duration, button=button)
        else:
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
            # Calculate duration based on distance
            current_x, current_y = pyautogui.position()
            duration = self._calculate_duration(current_x, current_y, x, y)
            if self.use_bezier:
                self._move_along_bezier(x, y, duration=duration)
            else:
                pyautogui.moveTo(x, y, duration=duration)

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

    def screenshot_with_grid(
        self, rows: int = 10, cols: int = 10
    ) -> Dict[str, Any]:
        """
        Take a screenshot with a labeled grid overlay for precise targeting.

        The grid uses alphanumeric labels: columns are A-Z (then AA, AB...),
        rows are 1-based numbers. Cell "A1" is top-left.

        Args:
            rows: Number of rows in the grid (default: 10)
            cols: Number of columns in the grid (default: 10)

        Returns:
            Dictionary containing:
                - image: Base64-encoded PNG with grid overlay
                - rows: Number of rows
                - cols: Number of columns
                - cell_width: Width of each cell in pixels
                - cell_height: Height of each cell in pixels
                - screen_width: Total screen width
                - screen_height: Total screen height
        """
        # Refresh screen size
        self._refresh_screen_size()

        # Take screenshot
        image = pyautogui.screenshot()
        draw = ImageDraw.Draw(image)

        # Calculate cell dimensions
        cell_width = self.screen_width / cols
        cell_height = self.screen_height / rows

        # Grid line color and label color
        grid_color = (255, 0, 0, 200)  # Red with some transparency
        label_color = (255, 255, 0)  # Yellow for labels
        label_bg_color = (0, 0, 0, 180)  # Semi-transparent black background

        # Try to use a reasonable font size based on cell dimensions
        font_size = max(10, min(int(cell_height / 4), int(cell_width / 4), 24))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Draw vertical lines and column labels
        for col in range(cols + 1):
            x = int(col * cell_width)
            draw.line([(x, 0), (x, self.screen_height)], fill=grid_color, width=2)

        # Draw horizontal lines and row labels
        for row in range(rows + 1):
            y = int(row * cell_height)
            draw.line([(0, y), (self.screen_width, y)], fill=grid_color, width=2)

        # Draw cell labels at the center of each cell
        for row in range(rows):
            for col in range(cols):
                label = self._get_grid_label(row, col)

                # Calculate label position (center of cell)
                label_x = int(col * cell_width + cell_width / 2)
                label_y = int(row * cell_height + cell_height / 2)

                # Get text bounding box for centering
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Center the label
                text_x = label_x - text_width // 2
                text_y = label_y - text_height // 2

                # Draw background rectangle for readability
                padding = 2
                draw.rectangle(
                    [
                        text_x - padding,
                        text_y - padding,
                        text_x + text_width + padding,
                        text_y + text_height + padding,
                    ],
                    fill=label_bg_color,
                )

                # Draw the label
                draw.text((text_x, text_y), label, fill=label_color, font=font)

        # Convert image to base64-encoded PNG
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "image": image_base64,
            "rows": rows,
            "cols": cols,
            "cell_width": cell_width,
            "cell_height": cell_height,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }

    def _get_grid_label(self, row: int, col: int) -> str:
        """
        Generate a grid cell label from row and column indices.

        Args:
            row: 0-indexed row number
            col: 0-indexed column number

        Returns:
            Label string like "A1", "B2", "AA10", etc.
        """
        # Generate column label (A-Z, then AA, AB, etc.)
        col_label = ""
        col_num = col
        while col_num >= 0:
            col_label = chr(ord('A') + (col_num % 26)) + col_label
            col_num = col_num // 26 - 1

        # Row is 1-indexed for display
        row_label = str(row + 1)

        return col_label + row_label

    def _parse_grid_label(self, label: str) -> Tuple[int, int]:
        """
        Parse a grid label into row and column indices.

        Args:
            label: Grid cell label like "A1", "B2", "AA10"

        Returns:
            Tuple of (row_index, col_index), both 0-indexed

        Raises:
            ValueError: If label format is invalid
        """
        label = label.upper().strip()

        # Find where letters end and numbers begin
        col_part = ""
        row_part = ""

        for char in label:
            if char.isalpha():
                if row_part:
                    raise ValueError(f"Invalid grid label format: {label}")
                col_part += char
            elif char.isdigit():
                row_part += char
            else:
                raise ValueError(f"Invalid character in grid label: {char}")

        if not col_part or not row_part:
            raise ValueError(f"Invalid grid label format: {label}")

        # Convert column letters to index (A=0, B=1, ..., Z=25, AA=26, etc.)
        col_index = 0
        for char in col_part:
            col_index = col_index * 26 + (ord(char) - ord('A') + 1)
        col_index -= 1  # Convert to 0-indexed

        # Convert row number to index (1-indexed to 0-indexed)
        row_index = int(row_part) - 1

        return (row_index, col_index)

    def get_grid_cell_center(
        self, label: str, rows: int = 10, cols: int = 10
    ) -> Tuple[int, int]:
        """
        Get the center pixel coordinates of a grid cell.

        Args:
            label: Grid cell label like "A1", "B2"
            rows: Total number of rows in the grid
            cols: Total number of columns in the grid

        Returns:
            Tuple of (x, y) pixel coordinates at center of cell

        Raises:
            ValueError: If label is invalid or out of grid bounds
        """
        self._refresh_screen_size()

        row_index, col_index = self._parse_grid_label(label)

        # Validate bounds
        if row_index < 0 or row_index >= rows:
            raise ValueError(
                f"Row index {row_index + 1} out of bounds (1-{rows})"
            )
        if col_index < 0 or col_index >= cols:
            max_col_label = self._get_grid_label(0, cols - 1).rstrip('1')
            raise ValueError(
                f"Column index out of bounds (A-{max_col_label})"
            )

        # Calculate cell dimensions
        cell_width = self.screen_width / cols
        cell_height = self.screen_height / rows

        # Calculate center of cell
        center_x = int(col_index * cell_width + cell_width / 2)
        center_y = int(row_index * cell_height + cell_height / 2)

        return (center_x, center_y)

    def click_grid_cell(
        self,
        label: str,
        rows: int = 10,
        cols: int = 10,
        button: Literal["left", "right", "middle"] = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> Tuple[int, int]:
        """
        Click at the center of a grid cell.

        Args:
            label: Grid cell label like "A1", "B2"
            rows: Total number of rows in the grid
            cols: Total number of columns in the grid
            button: Mouse button to click
            clicks: Number of clicks
            interval: Time between clicks

        Returns:
            Tuple of (x, y) coordinates where click occurred

        Raises:
            ValueError: If label is invalid or out of bounds
        """
        x, y = self.get_grid_cell_center(label, rows, cols)
        self.click(x, y, button, clicks, interval)
        return (x, y)

    def get_cell_bounds(
        self, label: str, rows: int = 12, cols: int = 12
    ) -> Tuple[int, int, int, int]:
        """
        Get the pixel bounds of a grid cell.

        Args:
            label: Grid cell label like "A1", "B2"
            rows: Total number of rows in the grid
            cols: Total number of columns in the grid

        Returns:
            Tuple of (x, y, width, height) for the cell

        Raises:
            ValueError: If label is invalid or out of grid bounds
        """
        self._refresh_screen_size()
        row_index, col_index = self._parse_grid_label(label)

        # Validate bounds
        if row_index < 0 or row_index >= rows:
            raise ValueError(f"Row index {row_index + 1} out of bounds (1-{rows})")
        if col_index < 0 or col_index >= cols:
            max_col_label = self._get_grid_label(0, cols - 1).rstrip('1')
            raise ValueError(f"Column index out of bounds (A-{max_col_label})")

        cell_width = self.screen_width / cols
        cell_height = self.screen_height / rows

        x = int(col_index * cell_width)
        y = int(row_index * cell_height)

        return (x, y, int(cell_width), int(cell_height))

    def screenshot_refined_cell(
        self,
        cell: str,
        parent_rows: int = 12,
        parent_cols: int = 12,
        sub_rows: int = 5,
        sub_cols: int = 5,
    ) -> Dict[str, Any]:
        """
        Take a screenshot of a specific cell with a sub-grid overlay for precision targeting.

        Args:
            cell: Parent grid cell label (e.g., "B3")
            parent_rows: Number of rows in the parent grid
            parent_cols: Number of columns in the parent grid
            sub_rows: Number of rows in the sub-grid
            sub_cols: Number of columns in the sub-grid

        Returns:
            Dictionary containing:
                - image: Base64-encoded PNG with sub-grid overlay
                - cell_x, cell_y: Top-left corner of the cell
                - cell_width, cell_height: Dimensions of the cell
                - sub_cell_width, sub_cell_height: Dimensions of each sub-cell
        """
        # Get cell bounds
        cell_x, cell_y, cell_width, cell_height = self.get_cell_bounds(
            cell, parent_rows, parent_cols
        )

        # Take full screenshot
        full_image = pyautogui.screenshot()

        # Crop to the cell
        cell_image = full_image.crop((
            cell_x,
            cell_y,
            cell_x + cell_width,
            cell_y + cell_height
        ))

        # Scale up the cropped image for better visibility
        scale_factor = 3
        scaled_width = cell_width * scale_factor
        scaled_height = cell_height * scale_factor
        cell_image = cell_image.resize(
            (scaled_width, scaled_height),
            Image.Resampling.LANCZOS
        )

        draw = ImageDraw.Draw(cell_image)

        # Calculate sub-cell dimensions (on scaled image)
        sub_cell_width = scaled_width / sub_cols
        sub_cell_height = scaled_height / sub_rows

        # Grid styling
        grid_color = (0, 255, 0, 200)  # Green for sub-grid
        label_color = (255, 255, 255)  # White labels
        label_bg_color = (0, 0, 0, 180)

        font_size = max(12, min(int(sub_cell_height / 3), int(sub_cell_width / 3), 20))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

        # Draw sub-grid lines
        for col in range(sub_cols + 1):
            x = int(col * sub_cell_width)
            draw.line([(x, 0), (x, scaled_height)], fill=grid_color, width=2)

        for row in range(sub_rows + 1):
            y = int(row * sub_cell_height)
            draw.line([(0, y), (scaled_width, y)], fill=grid_color, width=2)

        # Draw sub-cell labels
        for row in range(sub_rows):
            for col in range(sub_cols):
                label = self._get_grid_label(row, col)
                label_x = int(col * sub_cell_width + sub_cell_width / 2)
                label_y = int(row * sub_cell_height + sub_cell_height / 2)

                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = label_x - text_width // 2
                text_y = label_y - text_height // 2

                padding = 2
                draw.rectangle(
                    [text_x - padding, text_y - padding,
                     text_x + text_width + padding, text_y + text_height + padding],
                    fill=label_bg_color,
                )
                draw.text((text_x, text_y), label, fill=label_color, font=font)

        # Add border and title
        draw.rectangle(
            [0, 0, scaled_width - 1, scaled_height - 1],
            outline=(255, 255, 0),
            width=3
        )

        # Convert to base64
        buffer = io.BytesIO()
        cell_image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "image": image_base64,
            "cell_x": cell_x,
            "cell_y": cell_y,
            "cell_width": cell_width,
            "cell_height": cell_height,
            "sub_cell_width": cell_width / sub_cols,  # Actual pixel size, not scaled
            "sub_cell_height": cell_height / sub_rows,
        }

    def click_refined_cell(
        self,
        parent_cell: str,
        sub_cell: str,
        parent_rows: int = 12,
        parent_cols: int = 12,
        sub_rows: int = 5,
        sub_cols: int = 5,
        button: Literal["left", "right", "middle"] = "left",
        clicks: int = 1,
    ) -> Tuple[int, int]:
        """
        Click a sub-cell within a refined grid area.

        Args:
            parent_cell: Parent grid cell label (e.g., "B3")
            sub_cell: Sub-cell label within the parent (e.g., "A2")
            parent_rows: Rows in parent grid
            parent_cols: Columns in parent grid
            sub_rows: Rows in sub-grid
            sub_cols: Columns in sub-grid
            button: Mouse button to click
            clicks: Number of clicks

        Returns:
            Tuple of (x, y) coordinates where click occurred
        """
        # Get parent cell bounds
        cell_x, cell_y, cell_width, cell_height = self.get_cell_bounds(
            parent_cell, parent_rows, parent_cols
        )

        # Parse sub-cell
        sub_row, sub_col = self._parse_grid_label(sub_cell)

        # Validate sub-cell bounds
        if sub_row < 0 or sub_row >= sub_rows:
            raise ValueError(f"Sub-cell row {sub_row + 1} out of bounds (1-{sub_rows})")
        if sub_col < 0 or sub_col >= sub_cols:
            raise ValueError(f"Sub-cell column out of bounds")

        # Calculate sub-cell dimensions
        sub_cell_width = cell_width / sub_cols
        sub_cell_height = cell_height / sub_rows

        # Calculate center of sub-cell
        x = int(cell_x + sub_col * sub_cell_width + sub_cell_width / 2)
        y = int(cell_y + sub_row * sub_cell_height + sub_cell_height / 2)

        self.click(x, y, button, clicks)
        return (x, y)

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
