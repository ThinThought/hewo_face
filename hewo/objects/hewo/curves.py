"""Small vectorized curve helpers for face geometry."""

import numpy as np


def quadratic_basis(x_points, sample_count):
    """Return sample x coordinates and Lagrange weights for three x controls."""
    x0, x1, x2 = x_points
    xs = np.linspace(x0, x2, sample_count)
    weights = np.column_stack((
        ((xs - x1) * (xs - x2)) / ((x0 - x1) * (x0 - x2)),
        ((xs - x0) * (xs - x2)) / ((x1 - x0) * (x1 - x2)),
        ((xs - x0) * (xs - x1)) / ((x2 - x0) * (x2 - x1)),
    ))
    return xs, weights


def sample_quadratic(xs, weights, y_points):
    """Evaluate a quadratic through three controls and return integer points."""
    ys = weights @ np.asarray(y_points, dtype=float)
    return list(zip(xs.astype(int).tolist(), ys.astype(int).tolist()))


def through_point_bezier(start, middle, end, sample_count):
    """Quadratic Bezier from ``start`` to ``end`` whose midpoint height is ``middle``'s.

    Unlike a Lagrange parabola ``y(x)`` through three points, the curve is
    parametric: it never diverges when the end x coordinates approach the
    middle one, and it always stays inside the convex hull of its controls.
    The control point keeps ``middle``'s x and is lifted so that ``B(0.5)``
    has ``middle``'s y. With evenly spaced x controls this is exactly the same
    parabola the Lagrange interpolation produces.
    """
    (x0, y0), (x1, y1), (x2, y2) = start, middle, end
    control = np.array((x1, 2.0 * y1 - (y0 + y2) / 2.0))
    t = np.linspace(0.0, 1.0, sample_count)[:, None]
    points = (
        (1.0 - t) ** 2 * np.array((x0, y0), dtype=float)
        + 2.0 * (1.0 - t) * t * control
        + t ** 2 * np.array((x2, y2), dtype=float)
    )
    return [(int(round(x)), int(round(y))) for x, y in points.tolist()]
