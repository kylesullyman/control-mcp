#!/usr/bin/env python3
"""Diagnostic test for mouse movement accuracy."""

import time
import pyautogui
from src.control_mcp.mouse_control import MouseController

def test_accuracy():
    """Test the accuracy of mouse movements."""

    print("=== Mouse Movement Accuracy Test ===\n")

    # Initialize controller
    controller = MouseController(pixels_per_second=2000.0, use_bezier=True)

    # Get screen size
    width, height = controller.get_screen_size()
    print(f"Screen size: {width}x{height}\n")

    # Test targets
    test_cases = [
        (200, 200, "Top-left area"),
        (width // 2, height // 2, "Center"),
        (width - 200, height - 200, "Bottom-right area"),
        (500, 500, "Middle area"),
    ]

    print("Testing movement accuracy...\n")

    for target_x, target_y, description in test_cases:
        print(f"Test: {description}")
        print(f"  Target: ({target_x}, {target_y})")

        # Get current position before movement
        before_x, before_y = pyautogui.position()
        print(f"  Before: ({before_x}, {before_y})")

        # Move cursor
        controller.move_cursor(target_x, target_y)

        # Wait a bit for movement to complete
        time.sleep(0.2)

        # Get position after movement
        after_x, after_y = pyautogui.position()
        print(f"  After:  ({after_x}, {after_y})")

        # Calculate error
        error_x = abs(after_x - target_x)
        error_y = abs(after_y - target_y)
        error_distance = ((error_x ** 2) + (error_y ** 2)) ** 0.5

        print(f"  Error:  ({error_x}, {error_y}) - distance: {error_distance:.2f} pixels")

        if error_distance < 5:
            print("  ✅ Accurate (< 5 pixels)")
        elif error_distance < 20:
            print("  ⚠️  Moderate accuracy (5-20 pixels)")
        else:
            print("  ❌ Poor accuracy (> 20 pixels)")

        print()
        time.sleep(0.5)

    # Test with straight line movement
    print("\n=== Testing straight line movement ===")
    controller.use_bezier = False

    target_x, target_y = width // 2, height // 2
    print(f"Target: ({target_x}, {target_y})")

    before_x, before_y = pyautogui.position()
    print(f"Before: ({before_x}, {before_y})")

    controller.move_cursor(target_x, target_y, duration=0.5)
    time.sleep(0.2)

    after_x, after_y = pyautogui.position()
    print(f"After:  ({after_x}, {after_y})")

    error_distance = ((after_x - target_x) ** 2 + (after_y - target_y) ** 2) ** 0.5
    print(f"Error:  {error_distance:.2f} pixels")

    print("\n=== Test complete! ===")

if __name__ == "__main__":
    test_accuracy()
