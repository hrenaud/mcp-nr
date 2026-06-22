"""
Tests for _helpers.py validation functions.

Comprehensive coverage for:
- validate_themes: Theme ID validation (1-13)
- validate_score_range: Numeric range validation with boundaries
- validate_nonnegative: Non-negative value validation

Execution:
    cd /chemin/vers/projet
    pytest tests/test_helpers.py -v
"""

import sys
from pathlib import Path

# Ajouter le dossier files/ au path pour importer le module
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
from fastmcp.exceptions import ToolError
from mcp_ref_core import _helpers


class TestValidateThemes:
    """Test validate_themes function for theme ID validation."""

    def test_validate_themes_none_returns_all_themes(self):
        """Passing None should return list of all themes (1-13)."""
        result = _helpers.validate_themes(None)
        assert result == list(range(1, 14))
        assert len(result) == 13

    @pytest.mark.parametrize("themes", [
        [1],
        [13],
        [1, 13],
        [1, 7, 13],
        [5],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    ])
    def test_validate_themes_valid_themes(self, themes):
        """Valid theme IDs (1-13) should pass through unchanged."""
        result = _helpers.validate_themes(themes)
        assert result == themes

    @pytest.mark.parametrize("invalid_themes", [
        [0],
        [14],
        [99],
        [0, 1],
        [1, 14],
        [1, 50, 13],
        [-1],
        [-1, 0, 14, 15],
    ])
    def test_validate_themes_invalid_themes(self, invalid_themes):
        """Invalid theme IDs (outside 1-13) should raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_themes(invalid_themes)

        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower()
        assert "1 et 13" in error_msg

    def test_validate_themes_error_message_includes_invalid_values(self):
        """Error message should include the invalid values received."""
        invalid_list = [0, 14, 99]
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_themes(invalid_list)

        error_msg = str(exc_info.value)
        assert "[0" in error_msg
        assert "14" in error_msg
        assert "99" in error_msg


class TestValidateScoreRange:
    """Test validate_score_range function for numeric boundary validation."""

    @pytest.mark.parametrize("value,min_val,max_val", [
        (50, 0, 100),       # Middle of range
        (0, 0, 100),        # At minimum boundary
        (100, 0, 100),      # At maximum boundary
        (1, 1, 1),          # Single valid value
        (-50, -100, 0),     # Negative range
        (0, -50, 50),       # Zero in range
        (5, 1, 10),         # Small range
    ])
    def test_validate_score_range_valid_values(self, value, min_val, max_val):
        """Values within range (inclusive) should pass without raising."""
        # Should not raise
        _helpers.validate_score_range(value, min_val, max_val, "test_param")

    @pytest.mark.parametrize("value,min_val,max_val", [
        (-1, 0, 100),       # Below minimum
        (101, 0, 100),      # Above maximum
        (1, 2, 10),         # Below minimum
        (11, 2, 10),        # Above maximum
        (-101, -100, 0),    # Below minimum in negative range
        (1, -50, 0),        # Above maximum in negative range
    ])
    def test_validate_score_range_out_of_range(self, value, min_val, max_val):
        """Values outside range should raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_score_range(value, min_val, max_val, "test_param")

        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower()
        assert str(min_val) in error_msg
        assert str(max_val) in error_msg
        assert str(value) in error_msg

    def test_validate_score_range_error_message_includes_param_name(self):
        """Error message should include the parameter name."""
        param_name = "impact_score"
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_score_range(150, 0, 100, param_name)

        error_msg = str(exc_info.value)
        assert param_name in error_msg

    @pytest.mark.parametrize("param_name", [
        "impact_min",
        "priorite_min",
        "custom_param",
        "x",
    ])
    def test_validate_score_range_different_param_names(self, param_name):
        """Error message should accurately reflect different parameter names."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_score_range(150, 0, 100, param_name)

        error_msg = str(exc_info.value)
        assert param_name in error_msg

    def test_validate_score_range_just_below_min(self):
        """Value just below minimum should raise ToolError."""
        with pytest.raises(ToolError):
            _helpers.validate_score_range(-1, 0, 100, "param")

    def test_validate_score_range_just_above_max(self):
        """Value just above maximum should raise ToolError."""
        with pytest.raises(ToolError):
            _helpers.validate_score_range(101, 0, 100, "param")


class TestValidateNonnegative:
    """Test validate_nonnegative function for non-negative validation."""

    @pytest.mark.parametrize("value", [
        0,
        0.0,
        1,
        1.0,
        0.5,
        42,
        42.5,
        100.0,
        999999,
        0.0001,
    ])
    def test_validate_nonnegative_valid_values(self, value):
        """Non-negative values (>=0) should pass without raising."""
        # Should not raise
        _helpers.validate_nonnegative(value, "test_param")

    @pytest.mark.parametrize("value", [
        -1,
        -0.1,
        -1.0,
        -42,
        -42.5,
        -100,
        -999999,
        -0.0001,
    ])
    def test_validate_nonnegative_negative_values(self, value):
        """Negative values should raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_nonnegative(value, "test_param")

        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower()
        assert "0" in error_msg
        assert str(value) in error_msg

    def test_validate_nonnegative_zero_is_valid(self):
        """Zero should be accepted as valid (non-negative)."""
        # Critical boundary test
        _helpers.validate_nonnegative(0, "zero_test")
        _helpers.validate_nonnegative(0.0, "zero_float")

    def test_validate_nonnegative_error_message_includes_param_name(self):
        """Error message should include the parameter name."""
        param_name = "request_count"
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_nonnegative(-5, param_name)

        error_msg = str(exc_info.value)
        assert param_name in error_msg

    @pytest.mark.parametrize("param_name", [
        "dom_nodes",
        "requests",
        "size_kb",
        "custom_value",
    ])
    def test_validate_nonnegative_different_param_names(self, param_name):
        """Error message should accurately reflect different parameter names."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_nonnegative(-1, param_name)

        error_msg = str(exc_info.value)
        assert param_name in error_msg

    def test_validate_nonnegative_just_below_zero(self):
        """Value just below zero should raise ToolError."""
        with pytest.raises(ToolError):
            _helpers.validate_nonnegative(-0.0001, "param")

    def test_validate_nonnegative_just_above_zero(self):
        """Value just above zero should be valid."""
        _helpers.validate_nonnegative(0.0001, "param")
