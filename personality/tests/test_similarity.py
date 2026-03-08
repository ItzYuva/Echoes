"""
Tests for cosine similarity and distance computations.
"""

import math

import pytest

from personality.api.similarity import (
    cosine_similarity,
    euclidean_distance,
    profile_distance,
)
from personality.models.values_vector import ValuesVector


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self):
        a = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_similar_vectors(self):
        a = [0.7, 0.8, 0.6, 0.5, 0.4, 0.6, 0.7, 0.5]
        b = [0.6, 0.7, 0.5, 0.4, 0.3, 0.5, 0.6, 0.4]
        sim = cosine_similarity(a, b)
        assert sim > 0.95  # very similar

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector(self):
        a = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        b = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        assert cosine_similarity(a, b) == 0.0

    def test_all_half(self):
        a = [0.5] * 8
        b = [0.5] * 8
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            cosine_similarity([0.5, 0.5], [0.5])


class TestEuclideanDistance:
    """Test Euclidean distance computation."""

    def test_identical_vectors(self):
        a = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        assert euclidean_distance(a, a) == 0.0

    def test_opposite_corners(self):
        a = [0.0] * 8
        b = [1.0] * 8
        expected = math.sqrt(8)
        assert euclidean_distance(a, b) == pytest.approx(expected)

    def test_partial_difference(self):
        a = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b = [0.6, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        assert euclidean_distance(a, b) == pytest.approx(0.1)


class TestProfileDistance:
    """Test normalized profile distance via ValuesVector models."""

    def test_identical_profiles(self):
        a = ValuesVector(risk_tolerance=0.5, change_orientation=0.5)
        assert profile_distance(a, a) == 0.0

    def test_max_distance(self):
        a = ValuesVector(
            risk_tolerance=0.0, change_orientation=0.0, security_vs_growth=0.0,
            action_bias=0.0, social_weight=0.0, time_horizon=0.0,
            loss_sensitivity=0.0, ambiguity_tolerance=0.0,
        )
        b = ValuesVector(
            risk_tolerance=1.0, change_orientation=1.0, security_vs_growth=1.0,
            action_bias=1.0, social_weight=1.0, time_horizon=1.0,
            loss_sensitivity=1.0, ambiguity_tolerance=1.0,
        )
        assert profile_distance(a, b) == pytest.approx(1.0)


class TestValuesVectorSimilarity:
    """Test the similarity method on the Pydantic model itself."""

    def test_identical(self):
        v = ValuesVector(risk_tolerance=0.7, change_orientation=0.8)
        assert v.similarity(v) == pytest.approx(1.0)

    def test_different(self):
        a = ValuesVector(
            risk_tolerance=0.9, change_orientation=0.8,
            security_vs_growth=0.7, action_bias=0.6,
        )
        b = ValuesVector(
            risk_tolerance=0.2, change_orientation=0.3,
            security_vs_growth=0.4, action_bias=0.5,
        )
        sim = a.similarity(b)
        assert 0.0 < sim < 1.0

    def test_clamping(self):
        v = ValuesVector(risk_tolerance=1.5, change_orientation=-0.5)
        assert v.risk_tolerance == 1.0
        assert v.change_orientation == 0.0

    def test_to_list_order(self):
        v = ValuesVector(
            risk_tolerance=0.1, change_orientation=0.2,
            security_vs_growth=0.3, action_bias=0.4,
            social_weight=0.5, time_horizon=0.6,
            loss_sensitivity=0.7, ambiguity_tolerance=0.8,
        )
        expected = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        assert v.to_list() == expected
