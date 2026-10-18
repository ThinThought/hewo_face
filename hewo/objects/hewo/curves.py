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
