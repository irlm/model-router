"""Unit checks of the widget's data side, on synthetic data: the Agent-call classifier, the suggestions
(measured classes, the floor, effort and tier), and the per-change realized savings.
Run: python3 tools/test_status.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consumption  # noqa: E402
import status  # noqa: E402


def usage(by_class=None, rows=None):
    return {'main': {'rows': rows or []}, 'subagents': {'by_class': by_class or {}}}


class Classify(unittest.TestCase):
    def test_by_type_then_prompt(self):
        c = consumption.classify
        self.assertEqual(c('Web Researcher', 'x'), 'fact-lookup')
        self.assertEqual(c('Explore', 'find the parser'), 'code-explore')
        self.assertEqual(c('browser-tester', 'anything'), 'browser-flow')
        self.assertEqual(c('Evidence Collector', 'x'), 'browser-flow')
        self.assertEqual(c('Code Reviewer', 'x'), 'code-review')
        self.assertEqual(c('general-purpose', 'open http://x, click sign in, report pass/fail per item'), 'browser-flow')
        self.assertEqual(c('general-purpose', 'what is the default value of X'), 'fact-lookup')
        self.assertEqual(c('general-purpose', 'research the landscape and write a report'), 'research-synthesis')
        self.assertEqual(c('general-purpose', 'fix the failing test'), 'code-change')
        self.assertEqual(c('general-purpose', 'hello'), 'other')


class Suggest(unittest.TestCase):
    def test_measured_classes_and_the_floor(self):
        bc = {'code-explore': {'n': 16, 'cost': 24.71, 'types': {'Explore': 16}, 'models': {'claude-opus-5-5': {'n': 16, 'cost': 24.71}}, 'last': '2026-11-02T10:00'},
              'browser-flow': {'n': 45, 'cost': 30.0, 'types': {'browser-tester': 45}, 'models': {'claude-opus-5-5': {'n': 45, 'cost': 30.0}}, 'last': '2026-11-01T10:00'},
              'fact-lookup': {'n': 8, 'cost': 0.02, 'types': {'web-fetch': 6, 'Web Researcher': 2}, 'models': {'claude-haiku-5-5': {'n': 8, 'cost': 0.02}}, 'last': '2026-11-02T10:00'}}
        out = {g['id']: g for g in status.suggest(usage(bc), {})}
        self.assertEqual(out['explore']['kind'], 'measured')
        self.assertAlmostEqual(out['explore']['saving'][1], 24.71 - 16 * status.FIND_FEATURE_COST, 2)
        self.assertIn('last 2026-11-02', out['explore']['title'])
        self.assertAlmostEqual(out['browser']['saving'][1], 30.0 - 45 * status.BROWSER_FLOW_COST, 2)
        self.assertNotIn('lookups', out)   # a saving of $0.00 is under the floor

    def test_research_notes_measured_once_decided(self):
        bc = {'research-synthesis': {'n': 20, 'cost': 60.0, 'types': {'general-purpose': 20}, 'last': '2026-11-02T10:00',
                                     'models': {'claude-fable-5-1': {'n': 15, 'cost': 55.0}, 'claude-haiku-5-5': {'n': 5, 'cost': 0.5}}}}
        self.assertEqual(status.suggest(usage(bc), {})[0]['kind'], 'unmeasured')
        routing = {'families': {'research_synthesis': {'default': {'model': 'haiku', 'effort': 'low'}, 'evidence': {'haiku low': '18/18'},
                                                       'decided': {'evidence': {'claude-haiku-5-5 low': {'cost_per_success': 0.02}}}}}}
        g = status.suggest(usage(bc), {}, routing)[0]
        self.assertEqual((g['id'], g['kind']), ('synthesis', 'measured'))
        self.assertAlmostEqual(g['saving'][1], 55.0 - 15 * 0.02, 2)
        self.assertIn('15 research notes above haiku', g['title'])

    def test_haiku_calls_make_no_suggestion(self):
        bc = {'code-explore': {'n': 3, 'cost': 0.01, 'types': {'Explore': 3}, 'models': {'claude-haiku-5-5': {'n': 3, 'cost': 0.01}}, 'last': ''}}
        self.assertEqual(status.suggest(usage(bc), {}), [])

    def test_effort_and_tier(self):
        rows = [{'model': 'claude-fable-5-1', 'effort': 'xhigh', 'cost': 100.0, 'msgs': 10}]
        out = {g['id']: g for g in status.suggest(usage(rows=rows), {})}
        self.assertEqual(out['effort']['kind'], 'extrapolated')
        self.assertAlmostEqual(out['effort']['saving'][1], 100 * (1 - 1 / status.EFFORT_RATIO['xhigh']['claude-fable-5-1']), 2)
        self.assertEqual(out['tier']['kind'], 'unmeasured')
        self.assertEqual(out['tier']['saving'], [60.0, 63.0])


class Realized(unittest.TestCase):
    def test_each_change_in_its_own_window(self):
        events = [{'at': '2026-11-01T10:00Z', 'kind': 'mark', 'detail': 'effort low'},
                  {'at': '2026-11-02T10:00Z', 'kind': 'routing', 'detail': 'auto', 'projected': 5}]
        calls = [{'class': 'code-explore', 'ts': '2026-10-30T09:00', 'cost': 1.5, 'model': 'claude-opus-5-5'},
                 {'class': 'code-explore', 'ts': '2026-11-01T12:00', 'cost': 1.6, 'model': 'claude-opus-5-5'},
                 {'class': 'code-explore', 'ts': '2026-11-02T11:00', 'cost': 0.01, 'model': 'claude-haiku-5-5'},
                 {'class': 'code-explore', 'ts': '2026-11-02T12:00', 'cost': 0.01, 'model': 'claude-haiku-5-5'}]
        seg = lambda msgs, total, eff: {'main_msgs': msgs, 'main_total': total, 'main_rows': [{'model': 'm', 'effort': eff, 'msgs': msgs, 'cost': total}]}
        u = {'subagents': {'calls': calls}, 'segments': [seg(100, 20.0, 'xhigh'), seg(50, 5.0, 'low'), seg(10, 1.0, 'low')]}
        fam = [{'name': 'find_feature', 'last_check': {'verdict': 'ok', 'sample': '6', 'successes': '6'}}]
        latest, first = status.realized_savings(u, events, fam)['history']
        self.assertEqual((latest['kind'], latest['until']), ('routing', None))
        cls = latest['classes'][0]
        self.assertEqual((cls['class'], cls['before']['n'], cls['after']['n'], cls['check']['verdict']), ('code-explore', 1, 2, 'ok'))
        self.assertAlmostEqual(cls['saved'], (1.6 - 0.01) * 2, 2)
        self.assertAlmostEqual(latest['main']['saved'], 0.0, 2)                 # $0.10/msg on both sides
        self.assertEqual((first['until'], first['span']), ('2026-11-02T10:00Z', '24.0 h'))
        self.assertAlmostEqual(first['main']['saved'], (0.2 - 0.1) * 50, 2)    # per message, times the 50 after
        self.assertAlmostEqual(first['classes'][0]['saved'], (1.5 - 1.6) * 1, 2)

    def test_nothing_recorded(self):
        self.assertIsNone(status.realized_savings({'segments': None, 'subagents': {'calls': []}}, [], []))


if __name__ == '__main__':
    unittest.main()
