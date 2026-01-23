#!/usr/bin/env python3
"""Test that mouse cannot get closer than 5 pixels from screen edges."""

import time
import pyautogui
from src.control_mcp.mouse_control import MouseController, BORDER_MARGIN

def test_border_margin():
    """Test the 5-pixel border margin constraint."""

    print(f"=== {BORDER_MARGIN}-Pixel Border Margin Test ===\n")

    # Initialize controller
    controller = MouseController(pixels_per_second=2000.0, use_bezier=True)

    # Get screen size
    width, height = controller.get_screen_size()
    print(f"Screen size: {width}x{height}")
    print(f"Border margin: {BORDER_MARGIN} pixels\n")
    print(f"Allowed range:")
    print(f"  X: {BORDER_MARGIN} to {width - BORDER_MARGIN - 1}")
    print(f"  Y: {BORDER_MARGIN} to {height - BORDER_MARGIN - 1}\n")

    # Test cases: try to move to coordinates that should be clamped
    test_cases = [
        # (target_x, target_y, expected_x, expected_y, description)
        (0, 0, BORDER_MARGIN, BORDER_MARGIN, "Absolute top-left corner (0,0)"),
        (width, height, width - BORDER_MARGIN - 1, height - BORDER_MARGIN - 1, "Absolute bottom-right corner"),
        (0, height // 2, BORDER_MARGIN, height // 2, "Left edge (x=0)"),
        (width, height // 2, width - BORDER_MARGIN - 1, height // 2, "Right edge (x=width)"),
        (width // 2, 0, width // 2, BORDER_MARGIN, "Top edge (y=0)"),
        (width // 2, height, width // 2, height - BORDER_MARGIN - 1, "Bottom edge (y=height)"),
        (2, 2, BORDER_MARGIN, BORDER_MARGIN, "Very close to top-left (2,2)"),
        (width - 2, height - 2, width - BORDER_MARGIN - 1, height - BORDER_MARGIN - 1, "Very close to bottom-right"),
        (BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN, BORDER_MARGIN, "Exactly at margin (should work)"),
        (width - BORDER_MARGIN - 1, height - BORDER_MARGIN - 1, width - BORDER_MARGIN - 1, height - BORDER_MARGIN - 1, "Exactly at far margin"),
    ]

    print("Testing border clamping...\n")

    all_passed = True

    for target_x, target_y, expected_x, expected_y, description in test_cases:
        print(f"Test: {description}")
        print(f"  Requested: ({target_x}, {target_y})")
        print(f"  Expected:  ({expected_x}, {expected_y})")

        # Move cursor
        controller.move_cursor(target_x, target_y)
        time.sleep(0.1)

        # Get actual position
        actual_x, actual_y = pyautogui.position()
        print(f"  Actual:    ({actual_x}, {actual_y})")

        # Check if it matches expected
        if actual_x == expected_x and actual_y == expected_y:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL - Expected ({expected_x}, {expected_y}) but got ({actual_x}, {actual_y})")
            all_passed = False

        # Verify it's not too close to edges
        distance_to_left = actual_x
        distance_to_right = width - actual_x - 1
        distance_to_top = actual_y
        distance_to_bottom = height - actual_y - 1

        min_distance = min(distance_to_left, distance_to_right, distance_to_top, distance_to_bottom)

        if min_distance >= BORDER_MARGIN:
            print(f"  ✅ Margin respected (min distance: {min_distance}px)")
        else:
            print(f"  ❌ Margin violated! (min distance: {min_distance}px)")
            all_passed = False

        print()
        time.sleep(0.3)

    # Summary
    print("=" * 50)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print(f"✅ Mouse is properly constrained to stay {BORDER_MARGIN}px from edges")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Check the output above for details")

    # Return to center
    center_x, center_y = width // 2, height // 2
    controller.move_cursor(center_x, center_y)

if __name__ == "__main__":
    test_border_margin()
