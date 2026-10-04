# Input schema and usage

The renderer uses only the Python standard library. HTML, SVG, D2 source, and draw.io XML all come from the same JSON. It handles small layered structures and dependencies. Cycles remain visible; layout position does not imply execution order.

## Fields

Required top-level fields: `title`, `nodes`. Optional fields: `summary`, `kind`, `direction`, `as_of`, `edges`.

- `kind`: `progress` (default), `architecture`, `flow`, `dependency`, or `comparison`.
- `direction`: `LR` (default, left to right) or `TB` (top to bottom).
- `as_of`: The actual update time or snapshot identifier. When omitted, no timestamp is added; artifact generation time must not be mistaken for project update time.
- `nodes`: Each node requires a unique `id` and a short `label`. Prefer stable ASCII IDs; labels may use the user's language.
- `status`: `done`, `active`, `blocked`, `planned`, `unknown`, or `neutral` (no progress specified). Defaults to `unknown`, except for `architecture` and `comparison`, which default to `neutral`.
- Optional text details: `description`, `input`, `output`, `blocker`, `next_step`, and `validation`.
- Optional `layer`: An integer from 0 to 80 that changes presentation only, adding no execution order or dependency. The default layout centers nodes within topological layers. This hint can place supporting-evidence side inputs near their consumers; only real edges express task relationships.
- `validation`: A concrete completion criterion, such as "script executed", "artifact exists", or "acceptance check passed". It is supplied by the author, not inferred by the renderer.
- `evidence`: `[{"label": "Evidence description", "source": "File path, run record, or URL"}]`. Every `done` node requires at least one entry. The model using the skill must still check its truthfulness. HTTP/HTTPS URLs are clickable in the detail panel; local file paths appear as text.
- `edges`: Each edge requires `from` and `to`, with optional `type` (`sequence`, `data`, `dependency`, or `contains`) and `label`. The default type is `dependency`; default labels are English relationship names. Directions are prerequisite → dependent task, container → contained module, and data source → consumer.

`blocked` nodes require a nonempty blocking cause. For unknown nodes, explain what needs confirmation without guessing. Inputs are limited to 80 nodes; split dense diagrams into modules.

## Minimal example (fictional)

```json
{
  "title": "Example: Data processing progress",
  "kind": "progress",
  "summary": "Inputs checked, processing active, report waiting for results.",
  "nodes": [
    {
      "id": "input", "label": "Check inputs", "status": "done",
      "output": "Processable sample list", "validation": "Acceptance check passed",
      "evidence": [{"label": "Fictional sample-list check", "source": "example/check.log"}]
    },
    {"id": "process", "label": "Process data", "status": "active", "input": "Sample list", "next_step": "Inspect run outputs"},
    {"id": "report", "label": "Generate report", "status": "planned", "input": "Validated processing results"}
  ],
  "edges": [
    {"from": "input", "to": "process", "type": "data", "label": "Sample list"},
    {"from": "process", "to": "report", "type": "dependency"}
  ]
}
```

```bash
python3 <skill-dir>/scripts/render_brief.py brief.json --output-dir ./artifacts/visual-brief
```

Open `brief.html` and click nodes for details. Share `brief.svg` as a static diagram. `.d2` and `.drawio` are editable source files; their existence does not mean they were rendered or verified with third-party engines.

Open HTML in a system browser; chat links may show a source preview. Drag the file into the browser, or run `python3 <skill-dir>/scripts/serve_brief.py <brief.html>` for a local URL. A directory also works if it contains exactly one HTML file or an `index.html`. Distinguish temporary from lasting reports, and do not deliver only a `/tmp` directory path.

The interactive page supports node selection, diagram scrolling, fit-to-width, and original-size viewing. On narrow screens, labels remain readable and branches can be reached by scrolling or the node selector. Details appear beside the diagram on wide screens and below it on narrow screens. Diagram height is bounded by the viewport. Without JavaScript, native expandable sections still expose node details. Built-in interface labels are English; input text supports other languages.

## Optional third-party rendering

After confirming that `d2` is installed:

```bash
d2 ./artifacts/visual-brief/brief.d2 ./artifacts/visual-brief/brief-d2.svg
```

Import `.drawio` directly for manual editing. The default draw.io HTML export uses an online viewer; use this package's HTML for offline delivery.

- [D2 interaction](https://d2lang.com/tour/interactive/)
- [D2 SVG embedding](https://d2lang.com/tour/faq/)
- [draw.io HTML export](https://www.drawio.com/docs/manual/export/export-to-html/)
