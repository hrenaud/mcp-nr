import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_ref_core.auth import DynamicTokenVerifier, construire_verifier
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative


def test_dynamic_token_verifier_instantiates(tmp_path):
    verifier = DynamicTokenVerifier(tmp_path / "tokens.json")
    assert verifier is not None


def test_construire_verifier_returns_none_without_file(tmp_path):
    result = construire_verifier(tmp_path / "tokens.json")
    assert result is None


def test_validate_nonnegative_accepts_zero():
    validate_nonnegative(0, "dom")  # ne doit pas lever d'exception


def test_validate_score_range_rejects_negative():
    import pytest
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        validate_score_range(-1, 0, 100, "score")
