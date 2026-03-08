"""
Echoes Phase 2 -- Similarity Computations

Utility module for computing cosine similarity between values vectors.
Used by the Profile API and will be used by Phase 3 retrieval.
"""

from __future__ import annotations

import math
from typing import List

from personality.models.values_vector import ValuesVector


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector (same length as a).

    Returns:
        Float in [-1.0, 1.0]. 1.0 = identical direction.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """Compute Euclidean distance between two vectors.

    Useful for understanding how "far apart" two profiles are.

    Returns:
        Non-negative float. 0.0 = identical.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def profile_distance(vec_a: ValuesVector, vec_b: ValuesVector) -> float:
    """Compute normalized distance between two profiles.

    Returns:
        Float in [0.0, 1.0]. 0.0 = identical, 1.0 = maximally different.
    """
    dist = euclidean_distance(vec_a.to_list(), vec_b.to_list())
    # Max possible Euclidean distance for 8 dimensions with range [0, 1] is sqrt(8)
    max_dist = math.sqrt(8)
    return dist / max_dist
