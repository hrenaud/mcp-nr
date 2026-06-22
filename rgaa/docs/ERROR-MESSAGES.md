# Improved Error Messages — RGAA Server API

> **Version:** 1.4.0
> **Updated:** 2026-04-24
> **Focus:** Structured error responses with actionable guidance

## Overview

Error responses now include structured JSON with:
- **erreur** — Clear description of what went wrong
- **conseil** — Actionable guidance for the user
- **Additional context** — Input examples, accepted values, or format hints

This improves user experience and client error handling.

---

## Error Message Format

All error responses return a dictionary with required and optional fields:

```json
{
  "erreur": "Clear error message describing the problem",
  "conseil": "Actionable guidance for how to fix the problem",
  "[context_field]": "Additional context specific to the error"
}
```

### Example: Invalid Criterion ID

```python
result = client.rgaa_obtenir_critere("99.99")

# Returns:
{
  "erreur": "Critère '99.99' non trouvé dans le référentiel RGAA.",
  "conseil": "Vérifiez l'identifiant (ex: '1.1', '6.2'). Utilisez rgaa_lister_criteres pour voir tous les critères.",
  "critere_demande": "99.99",
  "exemples": ["1.1", "1.2", "6.1"]
}
```

---

## Tools with Improved Error Messages

### 1. rgaa_obtenir_critere

**Error Case:** Invalid criterion ID

```json
{
  "erreur": "Critère 'XX.YY' non trouvé.",
  "conseil": "Vérifiez l'identifiant (ex: '1.1'). Utilisez rgaa_lister_criteres.",
  "critere_demande": "XX.YY",
  "exemples": ["1.1", "1.2"]
}
```

---

### 2. rgaa_criteres_audit

**Error Case:** Invalid audit type

```json
{
  "erreur": "Type d'audit 'invalid' non reconnu.",
  "conseil": "Utilisez l'un des types valides.",
  "valeurs_acceptees": ["complet", "rapide", "complementaire"],
  "type_demande": "invalid"
}
```

**Error Case:** Invalid type parameter (non-string)

```json
{
  "erreur": "Paramètre 'type' invalide (doit être string).",
  "conseil": "Vérifiez le type du paramètre. Valeurs acceptées : complet, rapide, complementaire",
  "type_demande": "...",
  "type_acceptes": ["complet", "rapide", "complementaire"]
}
```

---

### 3. rgaa_analyser

**Error Case:** Invalid URL (network failure)

```json
{
  "erreur": "Analyse impossible pour https://invalid-url.invalid",
  "raison": "Connection error: name or service not known",
  "conseil": "Vérifiez que l'URL est accessible et valide.",
  "url": "https://invalid-url.invalid"
}
```

**Error Case:** Non-HTTP URL

```json
{
  "erreur": "Analyse impossible pour ftp://example.com",
  "raison": "Only HTTP/HTTPS URLs supported",
  "conseil": "Utilisez une URL HTTP ou HTTPS accessible publiquement.",
  "url": "ftp://example.com"
}
```

---

### 4. rgaa_checklist

**Error Case:** Invalid theme number

```json
{
  "erreur": "Thème(s) invalide(s) : [99]. Les thèmes doivent être entre 1 et 13.",
  "conseil": "Utilisez des thèmes valides ou omettez le paramètre pour tous les thèmes.",
  "exemple_themes": [1, 3, 6, 11]
}
```

**Error Case:** Invalid criteria format

```json
{
  "erreur": "Critère invalide : 'invalid'. Format attendu : 'X.Y' (ex: '1.1', '11.3')",
  "conseil": "Vérifiez le format des critères ou omettez le paramètre.",
  "exemple_criteres": ["1.1", "6.2", "11.3"]
}
```

---

### 5. rgaa_taux_conformite

**Error Case:** Empty results dictionary

```json
{
  "erreur": "Aucun résultat fourni.",
  "conseil": "Fournissez au moins un critère évalué avec son statut.",
  "format_attendu": {"1.1": "C", "1.2": "NC", "1.3": "NA"}
}
```

**Error Case:** Invalid status value

```json
{
  "erreur": "Statuts invalides : ['INVALID']",
  "statuts_acceptes": ["C", "NC", "NA"],
  "conseil": "C = Conforme, NC = Non Conforme, NA = Non Applicable"
}
```

**Error Case:** All results are NA (not applicable)

```json
{
  "erreur": "Aucun critère évalué (tous les critères sont NA).",
  "conseil": "Pour calculer le taux, fournissez au moins des résultats C ou NC.",
  "format_attendu": {"1.1": "C", "1.2": "NC", "1.3": "NA"}
}
```

---

## Error Message Patterns

### Pattern 1: Unknown Value (Not Found)
Used when user requests something that doesn't exist.

```json
{
  "erreur": "[Resource type] '[value]' non trouvé/reconnu.",
  "conseil": "Guidance on valid values or how to find them.",
  "[context]": "The invalid value or examples"
}
```

Examples:
- Invalid criterion ID → rgaa_obtenir_critere
- Invalid audit type → rgaa_criteres_audit

### Pattern 2: Invalid Format
Used when user provides incorrect input format.

```json
{
  "erreur": "[Field] invalide: '[value]'. Format attendu: '[format]'",
  "conseil": "How to fix the format.",
  "exemple_[field]": ["example1", "example2"]
}
```

Examples:
- Invalid criteria format → rgaa_checklist
- Invalid theme number → rgaa_checklist

### Pattern 3: External Service Error
Used when external calls (HTTP, network) fail.

```json
{
  "erreur": "[Operation] impossible pour [target]",
  "raison": "[Technical reason for failure]",
  "conseil": "What the user should check/fix",
  "[identifier]": "The target (URL, etc.)"
}
```

Examples:
- Network failure → rgaa_analyser
- Invalid URL → rgaa_analyser

### Pattern 4: Calculation/Processing Error
Used when input is structurally invalid for processing.

```json
{
  "erreur": "[Problem description]",
  "conseil": "How to provide valid input",
  "format_attendu": {"example": "structure"}
}
```

Examples:
- Empty results → rgaa_taux_conformite
- Invalid status → rgaa_taux_conformite

---

## Best Practices for Error Handling

### For API Users

1. **Check for error field:**
   ```python
   result = client.rgaa_obtenir_critere(criterion_id)
   if "erreur" in result:
       print(f"Error: {result['erreur']}")
       print(f"Solution: {result['conseil']}")
   ```

2. **Use examples to understand valid input:**
   ```python
   if "exemple_criteres" in result:
       print(f"Valid formats: {result['exemple_criteres']}")
   ```

3. **Log context for debugging:**
   ```python
   if "raison" in result:
       log.debug(f"Technical reason: {result['raison']}")
   ```

### For Client Implementations

1. **Validate open-world inputs** before calling tools with `openWorldHint=false`
2. **Provide user-friendly error messages** using the "conseil" field
3. **Show examples** from error responses to guide users toward valid inputs
4. **Implement retry logic** for `idempotentHint=true` tools that fail

---

## Version History

### v1.4.0 (2026-04-24)
- Added structured error messages to 5 tools
- All error responses include "conseil" field with actionable guidance
- Tool-specific context fields added (examples, valid values, formats)

### v1.3.0 and earlier
- Basic error messages (simple strings)
- No structured guidance

---

## Support

For questions about error message formats or error handling, contact the rgaa-mcp maintainers.
