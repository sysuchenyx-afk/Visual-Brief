#!/usr/bin/env python3
"""Render a factual brief into offline HTML, SVG, D2 and draw.io; stdlib only."""
import argparse
from collections import deque
import html
import json
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

STATUSES = {
    'done': ('Completed', '#16835d'), 'active': ('Active', '#357be5'),
    'blocked': ('Blocked', '#da5151'), 'planned': ('Planned', '#98691d'),
    'unknown': ('Unknown', '#8b68b5'), 'neutral': ('No progress specified', '#758399'),
}
RELATIONS = {'sequence': 'Sequence', 'data': 'Data flow', 'dependency': 'Dependency', 'contains': 'Contains'}
KINDS = {'progress', 'architecture', 'flow', 'dependency', 'comparison'}
DETAILS = ('description', 'input', 'output', 'blocker', 'next_step', 'validation')
NODE_W, NODE_H, MARGIN = 248, 116, 64


def string(value, field, required=False):
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f'{field} must be {"nonempty " if required else ""}text')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise ValueError(f'{field} contains unsupported control characters')
    return value


def normalize(raw):
    if not isinstance(raw, dict):
        raise ValueError('Input must be a JSON object')
    data = {key: string(raw.get(key, ''), key, key == 'title')
            for key in ('title', 'summary', 'as_of')}
    data['kind'] = raw.get('kind', 'progress')
    data['direction'] = raw.get('direction', 'LR')
    if data['kind'] not in KINDS or data['direction'] not in ('LR', 'TB'):
        raise ValueError('Unsupported kind or direction')
    nodes = raw.get('nodes')
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 80:
        raise ValueError('nodes must contain 1–80 nodes; split large diagrams by module')
    default = 'neutral' if data['kind'] in ('architecture', 'comparison') else 'unknown'
    data['nodes'], ids = [], set()
    for item in nodes:
        if not isinstance(item, dict):
            raise ValueError('Each node must be an object')
        node = {k: string(item.get(k, ''), f'node.{k}', True) for k in ('id', 'label')}
        if node['id'] in ids:
            raise ValueError(f'Duplicate node ID: {node["id"]}')
        ids.add(node['id'])
        node['status'] = item.get('status', default)
        if node['status'] not in STATUSES:
            raise ValueError(f'Unknown status: {node["status"]}')
        if 'layer' in item:
            if type(item['layer']) is not int or not 0 <= item['layer'] <= 80:
                raise ValueError(f'layer must be an integer from 0 to 80: {node["id"]}')
            node['layer'] = item['layer']
        node.update({k: string(item.get(k, ''), f'{node["id"]}.{k}') for k in DETAILS})
        evidence = item.get('evidence', [])
        if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
            raise ValueError('evidence must be an array of objects')
        node['evidence'] = [{k: string(e.get(k, ''), f'evidence.{k}', True)
                             for k in ('label', 'source')} for e in evidence]
        if node['status'] == 'done' and not evidence:
            raise ValueError(f'Completed nodes require evidence: {node["id"]}')
        if node['status'] == 'blocked' and not node['blocker'].strip():
            raise ValueError(f'Blocked nodes require a blocking cause: {node["id"]}')
        data['nodes'].append(node)
    edges = raw.get('edges', [])
    if not isinstance(edges, list):
        raise ValueError('edges must be an array')
    data['edges'] = []
    for item in edges:
        if not isinstance(item, dict):
            raise ValueError('Each edge must be an object')
        edge = {k: string(item.get(k, ''), f'edge.{k}', True) for k in ('from', 'to')}
        if edge['from'] not in ids or edge['to'] not in ids:
            raise ValueError(f'Edge references a missing node: {edge}')
        edge['type'] = item.get('type', 'dependency')
        if edge['type'] not in RELATIONS:
            raise ValueError(f'Unknown edge type: {edge["type"]}')
        edge['label'] = string(item.get('label', RELATIONS[edge['type']]), 'edge.label')
        data['edges'].append(edge)
    return data


def layout(data):
    ids = [n['id'] for n in data['nodes']]
    degree, children, rank = {i: 0 for i in ids}, {i: [] for i in ids}, {i: 0 for i in ids}
    for e in data['edges']:
        children[e['from']].append(e['to']); degree[e['to']] += 1
    queue, seen = deque(i for i in ids if degree[i] == 0), set()
    while queue:
        i = queue.popleft(); seen.add(i)
        for j in children[i]:
            rank[j] = max(rank[j], rank[i] + 1); degree[j] -= 1
            if degree[j] == 0:
                queue.append(j)
    # Retain cycles; deterministic fallback is a layout choice, not execution order.
    base = max((rank[i] for i in seen), default=-1) + 1
    for offset, i in enumerate(i for i in ids if i not in seen):
        rank[i] = base + offset
    for node in data['nodes']:
        if 'layer' in node:
            rank[node['id']] = node['layer']
    rows, pos = {}, {}
    for i in ids:
        rows.setdefault(rank[i], []).append(i)
    max_lanes = max(map(len, rows.values()))
    for i in ids:
        row = rows[rank[i]]
        lane = row.index(i) + (max_lanes - len(row)) / 2
        if data['direction'] == 'LR':
            pos[i] = (MARGIN + rank[i] * (NODE_W + 150), MARGIN + lane * (NODE_H + 74))
        else:
            pos[i] = (MARGIN + lane * (NODE_W + 70), MARGIN + rank[i] * (NODE_H + 110))
    width = max(x for x, y in pos.values()) + NODE_W + MARGIN
    axis = 0 if data['direction'] == 'LR' else 1
    step = NODE_W + 150 if axis == 0 else NODE_H + 110
    outer_count = sum(pos[e['to']][axis] - pos[e['from']][axis] != step for e in data['edges'])
    height = max(y for x, y in pos.values()) + NODE_H + MARGIN
    if outer_count:
        if axis == 0:
            height += 32 * outer_count + 48
        else:
            width += 32 * outer_count + 100
    return pos, width, height


def wrap_label(text, limit=26, lines=2):
    result, line, size = [], '', 0
    for c in text.replace('\n', ' '):
        unit = 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
        if size + unit > limit:
            result.append(line); line, size = '', 0
        line += c; size += unit
    if line:
        result.append(line)
    if len(result) > lines:
        result = result[:lines]; result[-1] = result[-1][:-1] + '…'
    return result


def svg(data, pos, width, height):
    esc = html.escape
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(data["title"], quote=True)}">',
             f'<title>{esc(data["title"])}</title>',
             '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" '
             'markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 Z" fill="#64748b"/></marker></defs>',
             '<style>.node-card{fill:#fff;stroke:#bac5d5;stroke-width:1.5}.node text,.edge-label{fill:#17243b;'
             'font-family:system-ui,sans-serif}.edge{fill:none;stroke:#64748b;stroke-width:1.6}'
             '.status-text{fill:#53627a}.edge-label{paint-order:stroke;stroke:#fff;stroke-width:5}</style>']
    outgoing = {n['id']: [] for n in data['nodes']}
    incoming = {n['id']: [] for n in data['nodes']}
    for k, e in enumerate(data['edges']):
        outgoing[e['from']].append(k); incoming[e['to']].append(k)
    outer_index = 0
    right = max(x for x, y in pos.values()) + NODE_W
    bottom = max(y for x, y in pos.values()) + NODE_H
    for k, e in enumerate(data['edges']):
        x1, y1 = pos[e['from']]; x2, y2 = pos[e['to']]
        source_port = (outgoing[e['from']].index(k) + 1) / (len(outgoing[e['from']]) + 1)
        target_port = (incoming[e['to']].index(k) + 1) / (len(incoming[e['to']]) + 1)
        spread = (source_port - .5) * 44 + (target_port - .5) * 30
        if data['direction'] == 'LR' and x2 - x1 == NODE_W + 150:
            sx, sy, tx, ty = x1 + NODE_W, y1 + NODE_H * source_port, x2, y2 + NODE_H * target_port
            mid = (sx + tx) / 2 + spread
            path = f'M{sx},{sy} H{mid} V{ty} H{tx}'
            lx, ly = mid, min(sy, ty) - 10
        elif data['direction'] == 'TB' and y2 - y1 == NODE_H + 110:
            sx, sy, tx, ty = x1 + NODE_W * source_port, y1 + NODE_H, x2 + NODE_W * target_port, y2
            mid = (sy + ty) / 2 + spread
            path = f'M{sx},{sy} V{mid} H{tx} V{ty}'
            lx, ly = (sx + tx) / 2 + 14, mid - 8
        elif data['direction'] == 'TB':
            # Skip-layer, reverse and self edges travel in an outer gutter.
            # Every horizontal segment is in an inter-layer gap, never a card.
            outer_x = right + 48 + 32 * outer_index
            outer_index += 1
            sx, sy, tx, ty = x1 + NODE_W * source_port, y1 + NODE_H, x2 + NODE_W * target_port, y2
            path = f'M{sx},{sy} V{sy+26} H{outer_x} V{ty-26} H{tx} V{ty}'
            lx, ly = (outer_x + tx) / 2, ty - 34
        else:
            outer_y = bottom + 36 + 32 * outer_index
            outer_index += 1
            sx, sy, tx, ty = x1 + NODE_W, y1 + NODE_H * source_port, x2, y2 + NODE_H * target_port
            path = f'M{sx},{sy} H{sx+26} V{outer_y} H{tx-26} V{ty} H{tx}'
            lx, ly = (sx + tx) / 2, outer_y - 8
        dash = ' stroke-dasharray="6 4"' if e['type'] == 'dependency' else ''
        short = wrap_label(e['label'], 20, 1)[0] if e['label'] else ''
        edge_title = RELATIONS[e['type']] + ': ' + e['label']
        parts.append(f'<path class="edge" data-from="{esc(e["from"], quote=True)}" '
                     f'data-to="{esc(e["to"], quote=True)}" data-edge-type="{e["type"]}" '
                     f'd="{path}" marker-end="url(#arrow)"{dash}><title>{esc(edge_title)}</title></path>')
        parts.append(f'<text class="edge-label" x="{lx}" y="{ly}" text-anchor="middle" font-size="12">'
                     f'<title>{esc(edge_title)}</title>{esc(short)}</text>')
    for node in data['nodes']:
        x, y = pos[node['id']]; status, color = STATUSES[node['status']]
        parts.append(f'<a class="node" href="#details" role="button" aria-pressed="false" '
                     f'data-node-id="{esc(node["id"], quote=True)}" aria-label="{esc(node["label"] + ", " + status, quote=True)}">')
        parts.append(f'<title>{esc(node["label"] + ": " + status)}</title>')
        parts.append(f'<rect class="node-card" x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="12"/>')
        parts.append(f'<circle cx="{x+20}" cy="{y+NODE_H-24}" r="5" fill="{color}"/>')
        for j, line in enumerate(wrap_label(node['label'])):
            parts.append(f'<text x="{x+18}" y="{y+32+j*24}" font-size="16" font-weight="500">{esc(line)}</text>')
        parts.append(f'<text class="status-text" x="{x+34}" y="{y+NODE_H-19}" font-size="13">{status}</text></a>')
    parts.append('</svg>')
    return '\n'.join(parts)


def d2_source(data):
    quote = lambda x: json.dumps(x, ensure_ascii=False)
    aliases = {n['id']: f'n{i}' for i, n in enumerate(data['nodes'])}
    lines = ['# Generated source; third-party rendering is not performed.',
             f'direction: {"right" if data["direction"] == "LR" else "down"}', '']
    for node in data['nodes']:
        status, color = STATUSES[node['status']]
        tooltip = '\n'.join([node['description']] + [f'{k}: {node[k]}' for k in DETAILS[1:] if node[k]]
                            + [f'{e["label"]}: {e["source"]}' for e in node['evidence']]).strip()
        lines.extend([f'{aliases[node["id"]]}: {quote(node["label"] + chr(10) + status)} {{',
                      f'  style.stroke: {quote(color)}', f'  tooltip: {quote(tooltip or status)}', '}'])
    for edge in data['edges']:
        suffix = ' {style.stroke-dash: 4}' if edge['type'] == 'dependency' else ''
        lines.append(f'{aliases[edge["from"]]} -> {aliases[edge["to"]]}: {quote(edge["label"])}{suffix}')
    return '\n'.join(lines) + '\n'


def drawio_source(data, pos, width, height):
    root = ET.Element('mxfile', host='app.diagrams.net')
    diagram = ET.SubElement(root, 'diagram', id='visual-brief', name=data['title'])
    model = ET.SubElement(diagram, 'mxGraphModel', page='1', pageWidth=str(width), pageHeight=str(height))
    cells = ET.SubElement(model, 'root')
    ET.SubElement(cells, 'mxCell', id='0'); ET.SubElement(cells, 'mxCell', id='1', parent='0')
    aliases = {n['id']: f'n{i}' for i, n in enumerate(data['nodes'])}
    for node in data['nodes']:
        status, color = STATUSES[node['status']]
        obj = ET.SubElement(cells, 'object', id=aliases[node['id']], label=node['label'] + '\n' + status,
                            briefId=node['id'], briefStatus=node['status'],
                            briefDetails=json.dumps(node, ensure_ascii=False))
        cell = ET.SubElement(obj, 'mxCell', vertex='1', parent='1',
                             style=f'rounded=1;whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor={color};fontColor=#17243B;fontSize=16;')
        x, y = pos[node['id']]
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(NODE_W), height=str(NODE_H), attrib={'as': 'geometry'})
    for i, edge in enumerate(data['edges']):
        style = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;'
        if edge['type'] == 'dependency':
            style += 'dashed=1;'
        cell = ET.SubElement(cells, 'mxCell', id=f'e{i}', value=edge['label'], edge='1', parent='1',
                             source=aliases[edge['from']], target=aliases[edge['to']], style=style,
                             briefType=edge['type'])
        ET.SubElement(cell, 'mxGeometry', relative='1', attrib={'as': 'geometry'})
    ET.indent(root)
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


def fallback_details(data):
    esc = html.escape
    names = dict(zip(DETAILS, ('Description', 'Input', 'Output', 'Blocking cause', 'Next step', 'Completion criterion')))
    parts = ['<h2>All node details</h2>']
    for node in data['nodes']:
        parts.append(f'<details><summary>{esc(node["label"])} · {STATUSES[node["status"]][0]}</summary><dl>')
        for field, title in names.items():
            if node[field]:
                parts.append(f'<dt>{title}</dt><dd>{esc(node[field])}</dd>')
        if node['evidence']:
            parts.append('<dt>Evidence</dt><dd><ul>')
            for e in node['evidence']:
                parts.append(f'<li>{esc(e["label"])}: {esc(e["source"])}</li>')
            parts.append('</ul></dd>')
        parts.append('</dl></details>')
    return '\n'.join(parts)


def render(data):
    pos, width, height = layout(data)
    graphic = svg(data, pos, width, height)
    data['canvas'] = {'width': width, 'height': height}
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    embedded = serialized.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    legend = ''.join(f'<span><i class="dot" style="--status-color:{color}"></i>{label}</span>'
                     for key, (label, color) in STATUSES.items() if any(n['status'] == key for n in data['nodes']))
    values = {'TITLE': html.escape(data['title']), 'SUMMARY': html.escape(data['summary']),
              'AS_OF': html.escape('Snapshot: ' + data['as_of']) if data['as_of'] else '',
              'LEGEND': legend, 'SVG': graphic, 'DATA': embedded, 'DETAILS': fallback_details(data)}
    template = (Path(__file__).resolve().parent.parent / 'assets' / 'brief-template.html').read_text(encoding='utf-8')
    document = re.sub(r'@@([A-Z_]+)@@', lambda m: values[m[1]], template)
    return {'html': document, 'svg': graphic, 'json': serialized + '\n',
            'd2': d2_source(data), 'drawio': drawio_source(data, pos, width, height)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--name', default='brief')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.name):
            raise ValueError('--name must start with a letter or digit and contain only letters, digits, underscores, or hyphens')
        data = normalize(json.loads(args.input.read_text(encoding='utf-8')))
        outputs = render(data)
        paths = {ext: args.output_dir / f'{args.name}.{ext}' for ext in outputs}
        for path in paths.values():
            if path.exists() and not args.overwrite:
                raise ValueError(f'File already exists: {path}; use --overwrite to update it explicitly')
            if path.resolve() == args.input.resolve():
                raise ValueError('Output must not overwrite the input; choose a different directory or filename prefix')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for ext, content in outputs.items():
            paths[ext].write_text(content, encoding='utf-8')
            print(paths[ext].resolve())
    except (ValueError, TypeError, OSError) as exc:
        print(f'Generation failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
