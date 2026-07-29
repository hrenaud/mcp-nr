# EcoIndex Impacts And DOM Counting Design

## Goal

Return EcoIndex greenhouse-gas and water impacts, and provide a reproducible
Playwright DOM-counting protocol that excludes SVG descendants and includes
open Shadow DOM trees.

## Scope

The GreenIT server continues to receive the three raw EcoIndex metrics. It
does not add a browser dependency or a URL-measurement tool. The caller uses
the documented JavaScript expression to produce `dom_nodes`.

## EcoIndex Impacts

`greenit/files/data.py` will derive two numeric values from the calculated
EcoIndex score, rounded to two decimal places:

- `greenhouse_gases_g`: `2 + 2 * (50 - score) / 100`, in grams CO2e.
- `water_consumption_cl`: `3 + 3 * (50 - score) / 100`, in centilitres.

These formulas match `cnumr/ecoindex_js` 1.x. The calculator result and the
`greenit_calculer_ecoindex` response will expose the two fields alongside
`score` and `grade`. The MCP output schema will declare their units.

## DOM Measurement

The guide, the EcoIndex tool documentation, and the `audit_ecoindex` prompt
will use the same Playwright page-evaluation script. It counts each element in
the document and recursively in every accessible `shadowRoot`, with these
rules:

- Count a `<svg>` element itself.
- Exclude every descendant of a `<svg>` element, including a shadow tree
  attached below such a descendant.
- Recurse only into open Shadow DOM roots, the only roots accessible to page
  JavaScript.

The script is:

```js
const countDomNodes = (root) =>
  [...root.querySelectorAll('*')].reduce((total, element) => {
    if (element.parentElement?.closest('svg')) return total;
    return total + 1 + (element.shadowRoot ? countDomNodes(element.shadowRoot) : 0);
  }, 0);

return countDomNodes(document);
```

## Tests

- Unit tests for the calculator assert both impact fields and their values for
  a known score.
- MCP tool tests assert that the serialized response contains the two impact
  fields and values.
- Documentation/prompt tests assert the protocol explicitly mentions SVG and
  Shadow DOM handling.

## Error Handling

Existing non-negative validation for raw metrics remains unchanged. Closed
Shadow DOM is intentionally not counted because browser page JavaScript cannot
inspect it.
