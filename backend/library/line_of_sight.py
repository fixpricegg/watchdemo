
import numpy as np


def trace_segment(start, end, triangles, chunk_size=4096):
    start = np.asarray(start, dtype=np.float64)
    end = np.asarray(end, dtype=np.float64)
    triangles = np.asarray(triangles, dtype=np.float64)

    if start.shape != (3,) or end.shape != (3,):
        raise ValueError("Start and end must be 3D points")

    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
        raise ValueError("Triangles must have shape (N, 3, 3)")

    if not (
        np.isfinite(start).all()
        and np.isfinite(end).all()
        and np.isfinite(triangles).all()
    ):
        raise ValueError("Coordinates must be finite")

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    direction = end - start
    length = np.linalg.norm(direction)

    if length < 1e-9:
        return {
            "status": "degenerate_segment",
            "hit": None,
        }

    closest_t = None
    closest_index = None
    epsilon = 1e-9

    for offset in range(0, len(triangles), chunk_size):
        batch = triangles[offset:offset + chunk_size]

        v0 = batch[:, 0]
        edge1 = batch[:, 1] - v0
        edge2 = batch[:, 2] - v0

        p = np.cross(direction, edge2)
        det = np.einsum("ij,ij->i", edge1, p)

        valid = np.abs(det) > epsilon

        inv_det = np.zeros_like(det)
        inv_det[valid] = 1.0 / det[valid]

        tvec = start - v0
        u = np.einsum("ij,ij->i", tvec, p) * inv_det

        q = np.cross(tvec, edge1)
        v = np.einsum("ij,j->i", q, direction) * inv_det

        t = np.einsum("ij,ij->i", edge2, q) * inv_det

        hits = (
            valid
            & (u >= -epsilon)
            & (v >= -epsilon)
            & (u + v <= 1 + epsilon)
            & (t > epsilon)
            & (t < 1 - epsilon)
        )

        indices = np.flatnonzero(hits)

        if len(indices) == 0:
            continue

        best = indices[np.argmin(t[indices])]
        candidate_t = float(t[best])

        if closest_t is None or candidate_t < closest_t:
            closest_t = candidate_t
            closest_index = offset + int(best)

    if closest_t is None:
        return {
            "status": "no_intersection",
            "hit": None,
        }

    point = start + direction * closest_t

    return {
        "status": "intersection",
        "hit": {
            "triangle_index": closest_index,
            "fraction": round(closest_t, 8),
            "distance": round(float(length * closest_t), 4),
            "position": point.tolist(),
        },
    }
