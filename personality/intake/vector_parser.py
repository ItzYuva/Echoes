"""
Echoes Phase 2 -- Values Vector Parser

Extracts the [VALUES_VECTOR] JSON block from LLM output.
Built defensively -- LLMs are unreliable JSON generators and this
parser handles markdown fences, trailing commas, string-typed floats,
missing fields, and other common LLM quirks.
"""

from __future__ import annotations

import json
import re
from typing import Optional, Tuple

from config.logging_config import get_logger
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector

logger = get_logger(__name__)

# All dimension names in canonical order
DIMENSIONS = DIMENSION_NAMES


def parse_values_vector(raw: str) -> Tuple[Optional[ValuesVector], Optional[str]]:
    """Extract and parse a [VALUES_VECTOR] JSON block from LLM output.

    Args:
        raw: The full text response from the LLM.

    Returns:
        Tuple of (ValuesVector or None, closing_message or None).
        The closing message is the text BEFORE the [VALUES_VECTOR] marker.
    """
    # Find the [VALUES_VECTOR] marker (handle whitespace variations)
    marker_pattern = r"\[VALUES_VECTOR\]\s*:?\s*"
    match = re.search(marker_pattern, raw)

    if not match:
        logger.debug("No [VALUES_VECTOR] marker found in response")
        return None, None

    # Split into closing message and JSON portion
    closing_message = raw[: match.start()].strip()
    json_portion = raw[match.end() :].strip()

    # Extract JSON from the portion after the marker
    json_str = _extract_json(json_portion)
    if not json_str:
        logger.warning("Could not extract JSON after [VALUES_VECTOR] marker")
        return None, closing_message

    # Parse JSON
    data = _parse_json(json_str)
    if data is None:
        logger.warning("Failed to parse JSON from values vector block")
        return None, closing_message

    # Build ValuesVector
    vector = _build_vector(data)
    return vector, closing_message


def _extract_json(text: str) -> Optional[str]:
    """Extract a JSON object from text, handling markdown fences."""
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
        text = text.strip()

    # Find the first { and last matching }
    start = text.find("{")
    if start == -1:
        return None

    # Count braces to find the matching closing }
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # If we got here, braces are unmatched -- try adding a closing }
    return text[start:] + "}"


def _parse_json(json_str: str) -> Optional[dict]:
    """Parse JSON with forgiving error handling."""
    # First try clean parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Remove trailing commas (common LLM mistake)
    cleaned = re.sub(r",\s*([}\]])", r"\1", json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to fix unquoted keys
    cleaned2 = re.sub(r"(\w+)\s*:", r'"\1":', cleaned)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError as e:
        logger.warning("All JSON parse attempts failed: %s", e)
        return None


def _build_vector(data: dict) -> ValuesVector:
    """Build a ValuesVector from parsed JSON data.

    Handles:
    - String-typed floats ("0.7" -> 0.7)
    - Missing dimensions (filled with default 0.5)
    - Out-of-range values (clamped by Pydantic validator)
    """
    vector_data: dict = {}

    for dim in DIMENSIONS:
        if dim in data:
            val = data[dim]
            if isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    val = 0.5
            vector_data[dim] = val
        else:
            logger.warning("Missing dimension '%s', defaulting to 0.5", dim)
            vector_data[dim] = 0.5

    # Extract confidence notes
    confidence = data.get("confidence_notes", {})
    if isinstance(confidence, dict):
        vector_data["confidence_notes"] = confidence

    return ValuesVector(**vector_data)


def has_values_vector(text: str) -> bool:
    """Quick check if response contains the [VALUES_VECTOR] marker."""
    return "[VALUES_VECTOR]" in text
