#!/usr/bin/env python3
"""Test script for grid screenshot functionality."""

import base64
import sys
from pathlib import Path

# Add src to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from control_mcp.mouse_control import MouseController


def test_grid_screenshot():
    """Test grid screenshot and save to file."""
    # Create output directory for test screenshots
    output_dir = Path(__file__).parent / "test_screenshots"
    output_dir.mkdir(exist_ok=True)

    # Initialize mouse controller
    mouse = MouseController()

    # Get screen info
    width, height = mouse.get_screen_size()
    print(f"Screen size: {width}x{height}")

    # Test 1: Default grid (screen_height/36 x screen_width/36)
    print("\nTest 1: Default grid...")
    result = mouse.screenshot_with_grid()
    default_rows = result['rows']
    default_cols = result['cols']
    print(f"  Grid: {default_rows}x{default_cols}")
    print(f"  Cell size: {result['cell_width']:.1f}x{result['cell_height']:.1f} pixels")

    # Decode and save
    image_data = base64.b64decode(result['image'])
    default_path = output_dir / "grid_screenshot_default.png"
    with open(default_path, 'wb') as f:
        f.write(image_data)
    print(f"  Saved to: {default_path}")

    # Test 2: Custom grid (finer grid)
    print("\nTest 2: Custom finer grid (20x20)...")
    result_fine = mouse.screenshot_with_grid(rows=20, cols=20)
    print(f"  Grid: {result_fine['rows']}x{result_fine['cols']}")
    print(f"  Cell size: {result_fine['cell_width']:.1f}x{result_fine['cell_height']:.1f} pixels")

    image_data_fine = base64.b64decode(result_fine['image'])
    fine_path = output_dir / "grid_screenshot_20x20.png"
    with open(fine_path, 'wb') as f:
        f.write(image_data_fine)
    print(f"  Saved to: {fine_path}")

    # Test 3: Coarser grid
    print("\nTest 3: Coarser grid (6x8)...")
    result_coarse = mouse.screenshot_with_grid(rows=6, cols=8)
    print(f"  Grid: {result_coarse['rows']}x{result_coarse['cols']}")
    print(f"  Cell size: {result_coarse['cell_width']:.1f}x{result_coarse['cell_height']:.1f} pixels")

    image_data_coarse = base64.b64decode(result_coarse['image'])
    coarse_path = output_dir / "grid_screenshot_6x8.png"
    with open(coarse_path, 'wb') as f:
        f.write(image_data_coarse)
    print(f"  Saved to: {coarse_path}")

    print(f"\nAll tests completed! Screenshots saved to: {output_dir}")


if __name__ == "__main__":
    test_grid_screenshot()
