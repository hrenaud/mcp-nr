"""Validation helpers for GreenIT MCP server."""

from fastmcp.exceptions import ToolError


def validate_themes(themes: list[int] | None) -> list[int]:
    """
    Validate and normalize theme IDs.

    Args:
        themes: List of theme IDs to validate, or None for all themes

    Returns:
        Normalized list of valid theme IDs (1-13)

    Raises:
        ToolError: If any theme ID is outside [1-13]
    """
    if themes is None:
        return list(range(1, 14))

    invalid = [t for t in themes if not (1 <= t <= 13)]
    if invalid:
        raise ToolError(
            f"Les thèmes fournis sont invalides. Les thèmes doivent être entre 1 et 13. "
            f"Invalides reçus: {invalid}. Consulter rgaa_statistiques pour la liste complète."
        )

    return themes


def validate_score_range(value: int, min_val: int, max_val: int, param_name: str) -> None:
    """
    Validate numeric parameter is within specified range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        param_name: Parameter name for error message

    Raises:
        ToolError: If value is outside [min_val, max_val]
    """
    if not (min_val <= value <= max_val):
        raise ToolError(
            f"Les paramètres fournis sont invalides. `{param_name}` doit être entre "
            f"{min_val} et {max_val}, reçu: {value}."
        )


def validate_nonnegative(value: float, param_name: str) -> None:
    """
    Validate numeric parameter is non-negative.

    Args:
        value: Value to validate
        param_name: Parameter name for error message

    Raises:
        ToolError: If value is negative
    """
    if value < 0:
        raise ToolError(
            f"Les paramètres fournis sont invalides. `{param_name}` doit être ≥ 0, "
            f"reçu: {value}."
        )
