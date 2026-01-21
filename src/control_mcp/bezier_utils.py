"""Bezier curve utilities for smooth mouse movement."""

import random
from typing import List, Tuple


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


def generate_bezier_path(
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
