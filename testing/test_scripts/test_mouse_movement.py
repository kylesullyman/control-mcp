#!/usr/bin/env python3
"""Test script for mouse movement functionality."""

import time
from src.control_mcp.mouse_control import MouseController

def test_mouse_movement():
    """Test various mouse movement scenarios."""

    # Initialize controller with settings
    print("Initializing mouse controller...")
    controller = MouseController(pixels_per_second=2000.0, use_bezier=True)

    # Get screen size
    width, height = controller.get_screen_size()
    print(f"Screen size: {width}x{height}")

    # Get initial cursor position
    initial_x, initial_y = controller.get_cursor_position()
    print(f"\nInitial cursor position: ({initial_x}, {initial_y})")

    # Test 1: Short distance movement
    print("\n=== Test 1: Short distance movement ===")
    target_x, target_y = initial_x + 100, initial_y + 100
    print(f"Moving to ({target_x}, {target_y})...")
    start_time = time.time()
    controller.move_cursor(target_x, target_y)
    elapsed = time.time() - start_time
    final_x, final_y = controller.get_cursor_position()
    print(f"Final position: ({final_x}, {final_y})")
    print(f"Movement time: {elapsed:.3f}s")
    print(f"Distance: {((target_x - initial_x)**2 + (target_y - initial_y)**2)**0.5:.1f} pixels")
    time.sleep(0.5)

    # Test 2: Long distance movement
    print("\n=== Test 2: Long distance movement ===")
    target_x, target_y = width // 2, height // 2
    current_x, current_y = controller.get_cursor_position()
    print(f"Moving from ({current_x}, {current_y}) to center ({target_x}, {target_y})...")
    start_time = time.time()
    controller.move_cursor(target_x, target_y)
    elapsed = time.time() - start_time
    final_x, final_y = controller.get_cursor_position()
    print(f"Final position: ({final_x}, {final_y})")
    print(f"Movement time: {elapsed:.3f}s")
    distance = ((target_x - current_x)**2 + (target_y - current_y)**2)**0.5
    print(f"Distance: {distance:.1f} pixels")
    print(f"Effective speed: {distance/elapsed:.1f} pixels/second")
    time.sleep(0.5)

    # Test 3: Bezier curve visibility test (slow, long distance)
    print("\n=== Test 3: Bezier curve movement (slow for visibility) ===")
    target_x, target_y = width - 100, height - 100
    current_x, current_y = controller.get_cursor_position()
    print(f"Moving from ({current_x}, {current_y}) to ({target_x}, {target_y}) with 2s duration...")
    start_time = time.time()
    controller.move_cursor(target_x, target_y, duration=2.0)
    elapsed = time.time() - start_time
    final_x, final_y = controller.get_cursor_position()
    print(f"Final position: ({final_x}, {final_y})")
    print(f"Movement time: {elapsed:.3f}s")
    time.sleep(0.5)

    # Test 4: Multiple rapid movements
    print("\n=== Test 4: Multiple rapid movements ===")
    points = [
        (100, 100),
        (width - 100, 100),
        (width - 100, height - 100),
        (100, height - 100),
        (width // 2, height // 2)
    ]

    print("Moving cursor in a square pattern...")
    for i, (target_x, target_y) in enumerate(points, 1):
        print(f"  Point {i}: ({target_x}, {target_y})")
        controller.move_cursor(target_x, target_y)
        time.sleep(0.3)

    final_x, final_y = controller.get_cursor_position()
    print(f"Final position: ({final_x}, {final_y})")

    # Test 5: Test straight line vs bezier
    print("\n=== Test 5: Straight line movement (no bezier) ===")
    controller.use_bezier = False
    target_x, target_y = 100, 100
    current_x, current_y = controller.get_cursor_position()
    print(f"Moving from ({current_x}, {current_y}) to ({target_x}, {target_y}) in straight line...")
    start_time = time.time()
    controller.move_cursor(target_x, target_y, duration=1.0)
    elapsed = time.time() - start_time
    print(f"Movement time: {elapsed:.3f}s")

    # Restore bezier
    controller.use_bezier = True
    print("\n=== Test 6: Bezier movement (for comparison) ===")
    target_x, target_y = width - 100, height - 100
    current_x, current_y = controller.get_cursor_position()
    print(f"Moving from ({current_x}, {current_y}) to ({target_x}, {target_y}) with bezier curve...")
    start_time = time.time()
    controller.move_cursor(target_x, target_y, duration=1.0)
    elapsed = time.time() - start_time
    print(f"Movement time: {elapsed:.3f}s")

    # Return to initial position
    print("\n=== Returning to initial position ===")
    controller.move_cursor(initial_x, initial_y)
    final_x, final_y = controller.get_cursor_position()
    print(f"Returned to: ({final_x}, {final_y})")

    print("\n✅ All mouse movement tests completed!")

if __name__ == "__main__":
    test_mouse_movement()
