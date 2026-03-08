"""
Echoes Phase 2 -- Values Vector Model

The 8-dimensional psychological profile that defines how a user
approaches decisions. Each dimension is scored 0.0 to 1.0.
This vector drives personality-weighted story retrieval in Phase 3.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator

# Dimension names in canonical order (module-level for easy access)
DIMENSION_NAMES: list[str] = [
    "risk_tolerance",
    "change_orientation",
    "security_vs_growth",
    "action_bias",
    "social_weight",
    "time_horizon",
    "loss_sensitivity",
    "ambiguity_tolerance",
]


class ValuesVector(BaseModel):
    """8-dimensional decision-making personality profile.

    Each dimension captures a different axis of how someone
    approaches life decisions. Scored 0.0 (low) to 1.0 (high).
    """

    risk_tolerance: float = 0.5
    change_orientation: float = 0.5
    security_vs_growth: float = 0.5
    action_bias: float = 0.5
    social_weight: float = 0.5
    time_horizon: float = 0.5
    loss_sensitivity: float = 0.5
    ambiguity_tolerance: float = 0.5

    confidence_notes: Dict[str, str] = {}

    @field_validator(
        "risk_tolerance",
        "change_orientation",
        "security_vs_growth",
        "action_bias",
        "social_weight",
        "time_horizon",
        "loss_sensitivity",
        "ambiguity_tolerance",
        mode="before",
    )
    @classmethod
    def clamp_values(cls, v: object) -> float:
        """Clamp numeric values to [0.0, 1.0] range."""
        if isinstance(v, str):
            v = float(v)
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return float(v)

    # -- Accessors ------------------------------------------------------------

    def to_list(self) -> List[float]:
        """Return values as an ordered list for similarity computation."""
        return [getattr(self, dim) for dim in DIMENSION_NAMES]

    def to_dict(self) -> Dict[str, float]:
        """Return values as a dict (without confidence_notes)."""
        return {dim: getattr(self, dim) for dim in DIMENSION_NAMES}

    def similarity(self, other: ValuesVector) -> float:
        """Cosine similarity between two values vectors.

        Returns:
            Float in [-1.0, 1.0]. 1.0 = identical profiles,
            0.0 = orthogonal, negative = opposite.
        """
        a = self.to_list()
        b = other.to_list()
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def dimension_summary(self) -> Dict[str, str]:
        """Human-readable summary of each dimension."""
        labels = {
            "risk_tolerance": ("risk-averse", "risk-seeking"),
            "change_orientation": ("stability-seeking", "change-seeking"),
            "security_vs_growth": ("security-driven", "growth-driven"),
            "action_bias": ("deliberate/wait", "act fast"),
            "social_weight": ("independent", "relational"),
            "time_horizon": ("present-focused", "future-focused"),
            "loss_sensitivity": ("loss-fearful", "gain-excited"),
            "ambiguity_tolerance": ("needs clarity", "comfortable with grey"),
        }
        result = {}
        for dim in DIMENSION_NAMES:
            val = getattr(self, dim)
            low, high = labels[dim]
            if val < 0.35:
                result[dim] = f"Strongly {low}"
            elif val < 0.5:
                result[dim] = f"Leans {low}"
            elif val == 0.5:
                result[dim] = "Balanced"
            elif val < 0.65:
                result[dim] = f"Leans {high}"
            else:
                result[dim] = f"Strongly {high}"
        return result
