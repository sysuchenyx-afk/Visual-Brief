---
name: visual-brief
description: "Explain project progress, architecture, workflows, dependencies, and next steps with concise text and clear diagrams, optionally offline interactive HTML. Use for project status, framework, or visual briefing requests. Do not activate for incidental one-line status updates or ordinary factual questions."
---

# Visual Brief

Help the user understand the current state, structural relationships, and next steps through concise text and clear diagrams. Match the user's language by default. Honor explicit requests for a format, tool, or text-only answer.

## Turn facts into diagrams

- For progress briefings, read relevant conversation context, actual artifacts, and necessary run results. Distinguish planned work, executed work, existing outputs, and passed acceptance checks. Inspect only the evidence needed for this briefing.
- For architecture briefings, distinguish existing implementation from proposals. Use `neutral` for modules with no progress information; do not infer completion or planned work.
- Derive nodes, edges, and prose from the same factual snapshot. Mark missing information as `unknown` and state actual blocking causes. Do not calculate completion percentages without a denominator and a clear counting rule.
- Choose the diagram to fit the question: status-bearing workflows or dependency graphs for progress, layered structures for architecture, data flows for processing, phase dependencies for plans, and parallel structures for comparisons. Do not invent a sequence to force a linear diagram. Distinguish sequence, data, dependency, and containment edges.
- Prefer about 5–12 important nodes in an overview, with detail in node panels. Split complex structures by module. This readability guideline does not justify removing real relationships.

## Choose tools and deliverables

Check which tools are available and preserve the user's tool choice. Ordinary briefings do not require installing an entire drawing toolchain.

1. For interaction or no specified format, use the standard-library renderer below to generate self-contained HTML and SVG. Clicking nodes reveals inputs, outputs, evidence, blockers, and next steps. No network connection is required, and the source remains editable.
2. When D2 is available and suits the structure, render the exported `.d2` file with D2. Native links and tooltips are not a clickable detail panel. Inline the SVG into HTML to preserve SVG interaction; an `<img>` does not provide the same behavior. Keep the same nodes and facts if using another layout.
3. For manual editing, deliver the exported `.drawio` file. Open or export it with available tools when needed. Generating XML alone does not mean draw.io was invoked or verified.
4. Use GPT Image for conceptual illustrations or requested visual styles. Prefer structured diagrams for precise workflows. Follow the current environment's image generation guidance; if no image tool is available, explain that and deliver a usable structured diagram.
5. Mermaid is sufficient for small static explanations. When the user requests an image or HTML, generate the actual artifact instead of delivering only source code.

The bundled renderer does not call D2, draw.io, or image APIs. It produces usable HTML/SVG and two editable source formats. Do not label unrendered source files as verified third-party results.

## Use the bundled renderer

For the first generation, read [references/input-format.md](references/input-format.md), then create JSON from the current facts. Do not pass example data off as the user's project.

Replace `<skill-dir>` with the directory containing this `SKILL.md`, and write to a location permitted by the task:

```bash
python3 <skill-dir>/scripts/render_brief.py <brief.json> --output-dir <output-dir>
```

Outputs are `brief.html`, `brief.svg`, `brief.d2`, `brief.drawio`, and normalized `brief.json`. Use `--name <prefix>` for a custom filename prefix. Existing files are protected by default; add `--overwrite` when explicitly updating previous artifacts.

Deliver a specific HTML file link, not just a directory. Save lasting reports in an allowed persistent project directory; reserve `/tmp` for temporary checks. Chat file previews may not execute HTML/JavaScript and do not constitute browser validation. The user can drag the HTML file into a system browser, or use the local viewer:

```bash
python3 <skill-dir>/scripts/serve_brief.py <brief.html-or-output-directory>
```

This command serves only the chosen HTML and prints `http://127.0.0.1:<port>/`. The link works while the process runs; Ctrl+C stops it. It does not publish the report externally. Expandable node details remain available even if scripts do not execute.

`assets/brief-template.html` is a self-contained template that can be adapted to the user's needs. It has no external resources or online viewer. Its built-in controls and the renderer's default status/relationship labels are English; project text accepts the user's language. The built-in layout suits small structures. Use suitable tools for dense networks, swimlanes, and precise timelines; do not present an ordinary dependency graph as a Gantt chart.

## Update and verify

- Reuse stable node IDs when prior JSON exists, updating actual statuses and relationships. Describe changes only when reliable before/after snapshots exist. HTML does not read the project or refresh progress automatically.
- Check arrow directions, branches, completion evidence, and agreement between prose and diagrams. Pair colors with status text rather than relying on color alone.
- After generation, inspect labels in the user's language, occlusion, and layout. If browser tools are available, open the HTML, click nodes, confirm that details update, and check narrow-screen readability. Successful rendering does not establish scientific or business acceptance.
- For branching, merging, or cross-layer edges, check that lines do not cross unrelated cards, labels do not overlap, and important nodes remain visible. Place supporting-evidence side inputs near their consumers. Use node `layer` hints when needed to adjust presentation without changing actual relationships. Layout must not imply an invented prerequisite.
- Deliver a short explanation, a visible diagram, and the HTML link. Include source files when editing matters. Embed the actual SVG or exported image when chat supports it; otherwise provide artifact links and a visible Mermaid overview. Do not publish or create external sites by default.
- Stop once the real briefing is readable, clickable, and factually consistent. Additional styles, animation, and tool integrations can wait until requested.
