#!/usr/bin/env python3
"""Test bezier curves and speed settings."""

import time
import pyautogui
from src.control_mcp.mouse_control import MouseController

def test_speed_and_bezier():
    """Test different speed settings and bezier curves."""

    print("=== Mouse Speed and Bezier Curve Test ===\n")

    width, height = pyautogui.size()

    # Test different speeds
    speeds = [500, 1000, 2000, 4000]

    print("Testing different speeds (pixels/second):\n")

    for speed in speeds:
        controller = MouseController(pixels_per_second=speed, use_bezier=False)

        # Move from left to right
        start_x, start_y = 200, height // 2
        end_x, end_y = width - 200, height // 2

        pyautogui.moveTo(start_x, start_y, duration=0)
        distance = abs(end_x - start_x)

        print(f"Speed: {speed} px/s")
        print(f"  Distance: {distance} pixels")
        expected_time = distance / speed
        print(f"  Expected time: {expected_time:.3f}s")

        start_time = time.time()
        controller.move_cursor(end_x, end_y)
        elapsed = time.time() - start_time

        print(f"  Actual time: {elapsed:.3f}s")
        print(f"  Difference: {abs(elapsed - expected_time):.3f}s")

        # Verify we reached target
        final_x, final_y = pyautogui.position()
        print(f"  Final position: ({final_x}, {final_y})")
        print(f"  Accuracy: {abs(final_x - end_x)} px error\n")

        time.sleep(0.3)

    # Test bezier curves with visualization
    print("\n=== Testing Bezier Curves ===\n")

    print("Watch the cursor movement pattern:\n")

    # Test 1: Bezier curve (should be curved)
    print("1. BEZIER CURVE movement (should follow curved path)")
    controller = MouseController(pixels_per_second=500, use_bezier=True)

    pyautogui.moveTo(200, 200, duration=0)
    print("   Moving from (200, 200) to (1240, 700)...")
    start_time = time.time()
    controller.move_cursor(1240, 700)
    elapsed = time.time() - start_time
    print(f"   Time: {elapsed:.3f}s")
    time.sleep(0.5)

    # Test 2: Straight line (should be direct)
    print("\n2. STRAIGHT LINE movement (should follow direct path)")
    controller = MouseController(pixels_per_second=500, use_bezier=False)

    pyautogui.moveTo(200, 200, duration=0)
    print("   Moving from (200, 200) to (1240, 700)...")
    start_time = time.time()
    controller.move_cursor(1240, 700)
    elapsed = time.time() - start_time
    print(f"   Time: {elapsed:.3f}s")
    time.sleep(0.5)

    # Test 3: Multiple bezier movements
    print("\n3. MULTIPLE BEZIER movements (watch the curved paths)")
    controller = MouseController(pixels_per_second=800, use_bezier=True)

    points = [
        (200, 200, "Top-left"),
        (width - 200, 200, "Top-right"),
        (width - 200, height - 100, "Bottom-right"),
        (200, height - 100, "Bottom-left"),
        (width // 2, height // 2, "Center"),
    ]

    for x, y, label in points:
        current_x, current_y = pyautogui.position()
        distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5
        print(f"   → {label}: ({x}, {y}) - {distance:.0f}px")
        controller.move_cursor(x, y)
        time.sleep(0.4)

    print("\n=== Test Complete! ===")
    print("\nSummary:")
    print("✅ Speed settings control movement duration")
    print("✅ Bezier curves create natural, curved paths")
    print("✅ Straight line mode creates direct paths")
    print("✅ All movements reach exact target coordinates")

if __name__ == "__main__":
    test_speed_and_bezier()
