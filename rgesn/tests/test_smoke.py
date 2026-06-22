import sys
from pathlib import Path

# Ajouter les chemins pour l'import
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))


def test_import_rgesn_mcp():
    """Test que le module rgesn_mcp peut être importé"""
    import rgesn_mcp
    assert rgesn_mcp.VERSION == "0.1.0"


def test_mcp_instance_exists():
    """Test que l'instance MCP existe"""
    import rgesn_mcp
    assert rgesn_mcp.mcp is not None
