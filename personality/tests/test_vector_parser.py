"""
Tests for the values vector parser.

The parser is the most fragile part of the system since it depends
on LLM output being parseable. These tests cover every edge case.
"""

import pytest

from personality.intake.vector_parser import (
    has_values_vector,
    parse_values_vector,
    _extract_json,
    _parse_json,
    _build_vector,
)
from personality.models.values_vector import ValuesVector


class TestHasValuesVector:
    """Test the quick marker detection."""

    def test_present(self):
        assert has_values_vector("some text [VALUES_VECTOR] {}")

    def test_absent(self):
        assert not has_values_vector("some text without the marker")

    def test_partial(self):
        assert not has_values_vector("some [VALUES text")


class TestParseValuesVector:
    """Test the full parse pipeline."""

    def test_clean_output(self):
        raw = """Thanks for sharing all that. I have a good sense of where you're coming from.

[VALUES_VECTOR]
{
  "risk_tolerance": 0.7,
  "change_orientation": 0.8,
  "security_vs_growth": 0.65,
  "action_bias": 0.5,
  "social_weight": 0.4,
  "time_horizon": 0.6,
  "loss_sensitivity": 0.75,
  "ambiguity_tolerance": 0.55,
  "confidence_notes": {
    "risk_tolerance": "Strong signal"
  }
}"""
        vector, closing = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.7
        assert vector.change_orientation == 0.8
        assert vector.ambiguity_tolerance == 0.55
        assert "risk_tolerance" in vector.confidence_notes
        assert closing is not None
        assert "sharing" in closing

    def test_with_markdown_fences(self):
        raw = """Great conversation.

[VALUES_VECTOR]
```json
{
  "risk_tolerance": 0.3,
  "change_orientation": 0.4,
  "security_vs_growth": 0.5,
  "action_bias": 0.6,
  "social_weight": 0.7,
  "time_horizon": 0.8,
  "loss_sensitivity": 0.2,
  "ambiguity_tolerance": 0.9,
  "confidence_notes": {}
}
```"""
        vector, closing = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.3
        assert vector.ambiguity_tolerance == 0.9

    def test_with_colon_after_marker(self):
        raw = """Done.

[VALUES_VECTOR]:
{"risk_tolerance": 0.5, "change_orientation": 0.5, "security_vs_growth": 0.5, "action_bias": 0.5, "social_weight": 0.5, "time_horizon": 0.5, "loss_sensitivity": 0.5, "ambiguity_tolerance": 0.5}"""
        vector, closing = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.5

    def test_extra_text_after_json(self):
        raw = """Closing message.

[VALUES_VECTOR]
{"risk_tolerance": 0.6, "change_orientation": 0.7, "security_vs_growth": 0.5, "action_bias": 0.4, "social_weight": 0.3, "time_horizon": 0.8, "loss_sensitivity": 0.6, "ambiguity_tolerance": 0.5, "confidence_notes": {}}

I hope this helps you on your journey!"""
        vector, closing = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.6

    def test_missing_dimension(self):
        raw = """Done.

[VALUES_VECTOR]
{"risk_tolerance": 0.7, "change_orientation": 0.8}"""
        vector, _ = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.7
        assert vector.security_vs_growth == 0.5  # default

    def test_out_of_range_values(self):
        raw = """Done.

[VALUES_VECTOR]
{"risk_tolerance": 1.5, "change_orientation": -0.3, "security_vs_growth": 0.5, "action_bias": 0.5, "social_weight": 0.5, "time_horizon": 0.5, "loss_sensitivity": 0.5, "ambiguity_tolerance": 0.5}"""
        vector, _ = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 1.0  # clamped
        assert vector.change_orientation == 0.0  # clamped

    def test_string_typed_floats(self):
        raw = """Done.

[VALUES_VECTOR]
{"risk_tolerance": "0.7", "change_orientation": "0.8", "security_vs_growth": "0.5", "action_bias": "0.5", "social_weight": "0.5", "time_horizon": "0.5", "loss_sensitivity": "0.5", "ambiguity_tolerance": "0.5"}"""
        vector, _ = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.7

    def test_no_marker_returns_none(self):
        raw = "Just a normal response without any vector output"
        vector, closing = parse_values_vector(raw)
        assert vector is None
        assert closing is None

    def test_trailing_comma(self):
        raw = """Done.

[VALUES_VECTOR]
{"risk_tolerance": 0.7, "change_orientation": 0.8, "security_vs_growth": 0.5, "action_bias": 0.5, "social_weight": 0.5, "time_horizon": 0.5, "loss_sensitivity": 0.5, "ambiguity_tolerance": 0.5,}"""
        vector, _ = parse_values_vector(raw)
        assert vector is not None
        assert vector.risk_tolerance == 0.7


class TestExtractJson:
    """Test JSON extraction from text."""

    def test_simple_json(self):
        result = _extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_with_fences(self):
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert result is not None
        assert "key" in result

    def test_nested_braces(self):
        result = _extract_json('{"outer": {"inner": 1}}')
        assert result == '{"outer": {"inner": 1}}'

    def test_no_json(self):
        result = _extract_json("no json here")
        assert result is None

    def test_unmatched_braces(self):
        result = _extract_json('{"key": "value"')
        assert result is not None  # should append }


class TestParseJson:
    """Test forgiving JSON parsing."""

    def test_clean_json(self):
        result = _parse_json('{"a": 1, "b": 2}')
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma(self):
        result = _parse_json('{"a": 1, "b": 2,}')
        assert result is not None
        assert result["a"] == 1

    def test_invalid_json(self):
        result = _parse_json("not json at all")
        assert result is None


class TestBuildVector:
    """Test building a ValuesVector from parsed JSON."""

    def test_complete_data(self):
        data = {
            "risk_tolerance": 0.7,
            "change_orientation": 0.8,
            "security_vs_growth": 0.65,
            "action_bias": 0.5,
            "social_weight": 0.4,
            "time_horizon": 0.6,
            "loss_sensitivity": 0.75,
            "ambiguity_tolerance": 0.55,
            "confidence_notes": {"risk_tolerance": "Strong"},
        }
        vector = _build_vector(data)
        assert vector.risk_tolerance == 0.7
        assert vector.confidence_notes["risk_tolerance"] == "Strong"

    def test_partial_data(self):
        data = {"risk_tolerance": 0.9}
        vector = _build_vector(data)
        assert vector.risk_tolerance == 0.9
        assert vector.change_orientation == 0.5  # default

    def test_string_values(self):
        data = {"risk_tolerance": "0.7", "change_orientation": "0.3"}
        vector = _build_vector(data)
        assert vector.risk_tolerance == 0.7
        assert vector.change_orientation == 0.3
