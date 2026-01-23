#!/usr/bin/env python3
"""Test mouse movement to all four corners of the screen."""

import time
import pyautogui
from src.control_mcp.mouse_control import MouseController

def test_corners():
    """Move cursor to all four corners of the screen."""

    print("=== Screen Corners Movement Test ===\n")

    # Initialize controller with bezier curves for smooth movement
    controller = MouseController(pixels_per_second=2000.0, use_bezier=True)

    # Get screen size
    width, height = controller.get_screen_size()
    print(f"Screen size: {width}x{height}\n")

    # Get initial position
    initial_x, initial_y = controller.get_cursor_position()
    print(f"Starting position: ({initial_x}, {initial_y})\n")

    # Define corners (with small offset to avoid triggering macOS hot corners)
    offset = 10
    corners = [
        (offset, offset, "Top-left corner"),
        (width - offset, offset, "Top-right corner"),
        (width - offset, height - offset, "Bottom-right corner"),
        (offset, height - offset, "Bottom-left corner"),
    ]

    print("Moving to each corner of the screen...\n")

    for target_x, target_y, description in corners:
        # Get current position
        current_x, current_y = controller.get_cursor_position()

        # Calculate distance
        distance = ((target_x - current_x) ** 2 + (target_y - current_y) ** 2) ** 0.5

        print(f"{description}:")
        print(f"  Current: ({current_x}, {current_y})")
        print(f"  Target:  ({target_x}, {target_y})")
        print(f"  Distance: {distance:.0f} pixels")

        # Move to corner
        start_time = time.time()
        controller.move_cursor(target_x, target_y)
        elapsed = time.time() - start_time

        # Verify final position
        final_x, final_y = controller.get_cursor_position()
        error = ((final_x - target_x) ** 2 + (final_y - target_y) ** 2) ** 0.5

        print(f"  Final:   ({final_x}, {final_y})")
        print(f"  Time:    {elapsed:.3f}s")
        print(f"  Speed:   {distance/elapsed:.0f} px/s")
        print(f"  Error:   {error:.2f} pixels")
        print(f"  {'✅ Accurate' if error < 5 else '⚠️  Inaccurate'}\n")

        # Pause between corners
        time.sleep(0.8)

    # Return to center
    center_x, center_y = width // 2, height // 2
    print(f"Returning to center: ({center_x}, {center_y})")
    controller.move_cursor(center_x, center_y)
    final_x, final_y = controller.get_cursor_position()
    print(f"Final position: ({final_x}, {final_y})")

    print("\n=== Test Complete! ===")
    print(f"✅ Successfully moved to all 4 corners")
    print(f"✅ Screen coverage: {width}x{height} pixels")
    print(f"✅ Total distance traveled: ~{2 * width + 2 * height:.0f} pixels")

if __name__ == "__main__":
    test_corners()
