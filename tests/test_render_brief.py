"""Run with python3 -B -m unittest discover -s tests. Standard library only."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('brief', ROOT / 'scripts/render_brief.py')
BRIEF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIEF)
NS = '{http://www.w3.org/2000/svg}'


class BriefTest(unittest.TestCase):
    def test_exports_keep_nodes_and_relationships(self):
        raw = json.loads((ROOT / 'examples/brief.json').read_text(encoding='utf-8'))
        output = BRIEF.render(BRIEF.normalize(raw))
        svg = ET.fromstring(output['svg'])
        xml = ET.fromstring(output['drawio'])
        self.assertEqual({n.attrib['data-node-id'] for n in svg.findall(NS + 'a')},
                         {n['id'] for n in raw['nodes']})
        self.assertEqual([(e.attrib['data-from'], e.attrib['data-to'], e.attrib['data-edge-type'])
                          for e in svg.findall(NS + 'path')],
                         [(e['from'], e['to'], e['type']) for e in raw['edges']])
        exported = [json.loads(n.attrib['briefDetails']) for n in xml.findall('.//object')]
        self.assertEqual([(n['id'], n['label'], n['status']) for n in exported],
                         [(n['id'], n['label'], n['status']) for n in raw['nodes']])

    def test_unproven_completion_and_dangling_edges_rejected(self):
        raw = {'title': 'Example', 'nodes': [{'id': 'a', 'label': 'A'}]}
        for status in ('done', 'blocked'):
            bad = copy.deepcopy(raw)
            bad['nodes'][0]['status'] = status
            with self.assertRaises(ValueError):
                BRIEF.normalize(bad)
        bad = copy.deepcopy(raw)
        bad['edges'] = [{'from': 'a', 'to': 'missing'}]
        with self.assertRaises(ValueError):
            BRIEF.normalize(bad)

    def test_skip_layer_edge_does_not_cross_cards(self):
        ids = ['start', 'prepare', 'left', 'center', 'right', 'rank', 'first', 'second', 'final', 'context']
        pairs = [('start', 'prepare'), ('prepare', 'left'), ('prepare', 'center'),
                 ('prepare', 'right'), ('left', 'rank'), ('center', 'rank'),
                 ('right', 'rank'), ('rank', 'first'), ('first', 'second'),
                 ('second', 'final'), ('context', 'final')]
        data = BRIEF.normalize({'title': 'Branch/merge with a long side input', 'direction': 'TB',
            'nodes': [{'id': i, 'label': i} for i in ids],
            'edges': [{'from': a, 'to': b} for a, b in pairs]})
        output = BRIEF.render(data)
        svg = ET.fromstring(output['svg'])
        cards = [tuple(float(rect.attrib[k]) for k in ('x', 'y', 'width', 'height'))
                 for rect in svg.findall('.//' + NS + 'rect')]
        for edge in svg.findall(NS + 'path'):
            previous = None
            for command, values in re.findall(r'([MHV])([-\d.,]+)', edge.attrib['d']):
                values = [float(x) for x in values.split(',')]
                point = tuple(values) if command == 'M' else (
                    (values[0], previous[1]) if command == 'H' else (previous[0], values[0]))
                if previous is not None:
                    for x, y, width, height in cards:
                        if command == 'H':
                            crossing = (y + .1 < point[1] < y + height - .1
                                and max(min(previous[0], point[0]), x + .1)
                                < min(max(previous[0], point[0]), x + width - .1))
                        else:
                            crossing = (x + .1 < point[0] < x + width - .1
                                and max(min(previous[1], point[1]), y + .1)
                                < min(max(previous[1], point[1]), y + height - .1))
                        self.assertFalse(crossing, f'Edge {edge.attrib} crosses card {(x,y,width,height)}')
                previous = point

    def test_cycles_and_self_edges_retained(self):
        pairs = [('a', 'b'), ('b', 'a'), ('a', 'a')]
        data = BRIEF.normalize({'title': 'Cycle', 'nodes': [{'id': i, 'label': i} for i in ('a', 'b')],
            'edges': [{'from': a, 'to': b} for a, b in pairs]})
        svg = ET.fromstring(BRIEF.render(data)['svg'])
        self.assertEqual([(e.attrib['data-from'], e.attrib['data-to']) for e in svg.findall(NS + 'path')], pairs)

    def test_hostile_text_is_escaped_in_fallback_and_json(self):
        text = '</script><script>window.injected=true</script>'
        output = BRIEF.render(BRIEF.normalize({'title': text, 'nodes': [
            {'id': 'a', 'label': text, 'description': text}]}))
        self.assertNotIn(text, output['html'])
        self.assertIn('&lt;/script&gt;', output['html'])
        payload = re.search(r'<script type="application/json" id="brief-data">(.*?)</script>',
                            output['html'], re.S).group(1)
        self.assertEqual(json.loads(payload)['nodes'][0]['description'], text)


if __name__ == '__main__':
    unittest.main()
