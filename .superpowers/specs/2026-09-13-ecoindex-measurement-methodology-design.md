# EcoIndex Measurement Methodology Design

## Goal

Make the browser collection rules for `dom_nodes`, `requests`, and `size_kb`
discoverable through the GreenIT MCP. These rules are the only normalized
method accepted by the MCP for comparable EcoIndex scores.

## Interface

Add the read-only, parameterless tool
`greenit_obtenir_methodologie_ecoindex`. It returns a structured dictionary
containing:

- the normative status and comparability requirement;
- the collection rule, unit, and known limits for each metric;
- one complete browser JavaScript example without Lighthouse;
- the required collection sequence.

`greenit_calculer_ecoindex` remains a pure calculator. It receives only
`dom_nodes`, `requests`, and `size_kb`, with the optional URL retained as
context, and returns a dictionary rather than serialized JSON.

## Normalized collection

The JavaScript starts at `document.body`, which excludes `body` itself. It
counts descendant elements, recursively enters every open `shadowRoot`, and
does not count elements whose direct parent is an `<svg>`. Closed Shadow DOM
roots cannot be observed from page JavaScript and are reported as a limit.

Network requests are the current navigation entry plus all Resource Timing
entries. Transferred size is the sum of their `transferSize` values divided by
1024. Collection uses a cold browser context after the documented page-load
and scrolling sequence. Cached responses and cross-origin resources without
Timing-Allow-Origin can expose a zero transfer size; the methodology reports
this limitation.

## Documentation

The calculator description tells agents to call the methodology tool and
summarizes the DOM convention. The GreenIT README, development guide, HTTP
guide, root tool inventory, and changelog identify the methodology tool as the
single normalized source. The local EcoIndex evaluation skill must call this
tool instead of embedding a separate DOM formula.

## Tests

Tests first verify that the calculator returns a dictionary, the methodology
tool is registered and structured, and its JavaScript and limits cover classic
DOM, open Shadow DOM, direct SVG children, and closed Shadow DOM. Route and
documentation tests verify discoverability and the updated tool count.
