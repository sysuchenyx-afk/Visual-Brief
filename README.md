# Visual Brief

A Codex skill for explaining project progress, architecture, workflows, and dependencies with concise text, clear diagrams, and offline interactive HTML.

## Install and use

Place the complete repository in Codex's `skills/visual-brief` directory, keeping `SKILL.md`, `scripts`, `assets`, and `references` together. The default location is `~/.codex/skills/visual-brief`; if `CODEX_HOME` is set, use its `skills/visual-brief` subdirectory. Preserve an existing installation before replacing it.

For a first installation at the default location:

```bash
git clone https://github.com/sysuchenyx-afk/Visual-Brief.git ~/.codex/skills/visual-brief
```

Invoke the skill in a session that can discover it:

> Use `$visual-brief` to explain this project's current progress using real evidence. Create an overview diagram with statuses and dependencies, plus an HTML file with clickable node details.

Use it for architecture overviews, data flows, phase dependencies, and option comparisons as well. Diagrams distinguish completed, active, blocked, planned, and unknown work; completed nodes require evidence. Project content can use the user's language. The bundled viewer controls and diagnostic messages are in English.

## Generate diagrams without an LLM

Requires Python 3.9 or later. The bundled renderer uses only the standard library; no pip installation is needed.

```bash
python3 scripts/render_brief.py examples/brief.json --output-dir artifacts/example
```

This produces `brief.html`, `brief.svg`, `brief.json`, `brief.d2`, and `brief.drawio`. See [references/input-format.md](references/input-format.md) for the input schema. All example data is fictional and does not represent a real project's results.

Drag the HTML file into a system browser, or use the local viewer:

```bash
python3 scripts/serve_brief.py artifacts/example
```

Open the printed `http://127.0.0.1:<port>/` address. The link works while the process is running; press Ctrl+C to stop it. The page is self-contained and works offline, with node details, keyboard navigation, zoom, node selection, and dark mode. Expandable node details remain available when JavaScript is disabled.

## Tools and limitations

- The bundled renderer generates HTML and SVG, and exports editable D2 and draw.io source files. It does not invoke third-party rendering engines.
- The skill explains when to choose D2, draw.io, GPT Image, or Mermaid. Actual use depends on the tools available in the current environment.
- Statuses come from an explicit factual snapshot. The page does not fetch or refresh project progress automatically. Diagrams do not replace source evidence or business/scientific validation.
- The built-in layout suits small structures. Split dense networks into separate diagrams, or use dedicated tools for swimlanes and precise timelines.

## Repository files

```text
SKILL.md                    Skill instructions
agents/openai.yaml          Codex interface metadata
scripts/render_brief.py     Diagram generator
scripts/serve_brief.py      Local HTML viewer
assets/brief-template.html  Offline page template
references/input-format.md Input schema and tool guidance
examples/brief.json         Fictional example input
tests/test_render_brief.py  Export, status, and edge-routing checks
```

Run the checks:

```bash
python3 -B -m unittest discover -s tests
```
