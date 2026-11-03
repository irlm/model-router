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


class Learned(unittest.TestCase):
    def test_hot_cell_boundary_and_override(self):
        struggle = {'cells': {'-home-me-Projects-x': {'research-synthesis': {'n': 12, 'retries': 1, 'error_heavy': 4, 'failed': 0, 'struggled': 5, 'cost': 30.0, 'examples': ['a: 6 tool errors']}},
                              '-home-me-Projects-y': {'research-synthesis': {'n': 20, 'retries': 0, 'error_heavy': 1, 'failed': 0, 'struggled': 1, 'cost': 40.0, 'examples': []}}},
                    'sessions': {'-home-me-Projects-x': {'sessions': 2, 'msgs': 900, 'errors': 20, 'compactions': 6}}}
        routing = {'families': {'research_synthesis': {'default': {'model': 'sonnet', 'effort': 'low'}}}}
        out, sugg = status.learned_from(struggle, routing, {}, 0.25)
        hot = [c for c in out['cells'] if c['hot']]
        self.assertEqual([(c['class'], c['n']) for c in hot], [('research-synthesis', 12)])
        self.assertAlmostEqual(hot[0]['baseline'], 1 / 20, 3)
        self.assertEqual([(g['id'].split(':')[0], g['kind']) for g in sugg], [('learned', 'learned'), ('boundary', 'learned')])
        self.assertIn('/router prefer research-synthesis opus low', sugg[0]['action'])
        _, sugg2 = status.learned_from(struggle, routing, {'-home-me-Projects-x': {'research-synthesis': {'model': 'opus', 'effort': 'low'}}}, 0.25)
        self.assertEqual([g['id'].split(':')[0] for g in sugg2], ['boundary'])   # an override silences the cell

    def test_context_size_suggestion(self):
        struggle = {'cells': {}, 'sessions': {'-home-me-Projects-big': {'sessions': 1, 'msgs': 500, 'errors': 0, 'compactions': 0, 'ctx_per_msg': 300000,
                                                                       'read_cost': 90.0, 'write_cost': 10.0, 'idle_returns': 3, 'idle_cost': 4.0}}}
        _, sugg = status.learned_from(struggle, {}, {}, 0.25)
        self.assertEqual([g['id'].split(':')[0] for g in sugg], ['context'])
        self.assertAlmostEqual(sugg[0]['saving'][1], 90.0 * (300000 - 100000) / 300000, 2)
        self.assertIn('3 returns after an idle hour', sugg[0]['basis'])

    def test_small_cells_never_hot(self):
        struggle = {'cells': {'p': {'code-explore': {'n': 5, 'retries': 5, 'error_heavy': 0, 'failed': 0, 'struggled': 5, 'cost': 1.0, 'examples': []}}}, 'sessions': {}}
        out, sugg = status.learned_from(struggle, {}, {}, 0.25)
        self.assertFalse(out['cells'][0]['hot'])
        self.assertEqual(sugg, [])

    def test_reissued_call_is_marked(self):
        base = 'please research the kubernetes operator pattern and compare three frameworks for building operators with examples'
        calls = {'a': {'ts': '2026-11-01T10:00', 'session': 's', 'class': 'research-synthesis', 'prompt_text': base, 'description': ''},
                 'b': {'ts': '2026-11-01T10:30', 'session': 's', 'class': 'research-synthesis', 'prompt_text': base + ' round two, deeper', 'description': ''},
                 'c': {'ts': '2026-11-01T10:40', 'session': 's', 'class': 'code-explore', 'prompt_text': base, 'description': ''}}
        consumption.mark_retries(calls)
        self.assertEqual((calls['a']['retry_of'], calls['b']['retry_of'], calls['c']['retry_of']), (None, 'a', None))


class Verdicts(unittest.TestCase):
    def latest(self, classes, main, span='3.0 days'):
        return {'since': '2026-11-01T10:00Z', 'until': None, 'span': span, 'classes': classes, 'main': main}

    def test_states(self):
        side = lambda n, per, models: {'n': n, 'cost': n * per, 'per_call': per, 'models': models}
        cls = [{'class': 'code-explore', 'family': 'find_feature', 'saved': 3.0, 'check': None,
                'before': side(4, 1.5, {'claude-opus-5-5': 4}), 'after': side(6, 0.01, {'claude-haiku-5-5': 6})}]
        main = {'before': {'msgs': 500, 'cost': 60.0, 'per_msg': 0.12}, 'after': {'msgs': 200, 'cost': 20.0, 'per_msg': 0.1}, 'saved': 4.0,
                'rows': [{'model': 'claude-fable-5-1', 'effort': 'xhigh', 'before': {'msgs': 500, 'per_msg': 0.12}, 'after': {'msgs': 200, 'per_msg': 0.1}}]}
        sugg = [{'id': 'explore', 'saving': [20.0, 20.0]}, {'id': 'effort', 'saving': [80.0, 80.0]}, {'id': 'tier', 'saving': [100.0, 120.0]}, {'id': 'synthesis', 'saving': None}]
        import unittest.mock as um
        with um.patch.object(status, 'span_days', return_value=3.0):
            status.verdicts(sugg, self.latest(cls, main), 30)
        self.assertEqual(sugg[0]['real']['state'], 'holding')            # 3.0 over 3 days -> 30/window vs est 20
        self.assertAlmostEqual(sugg[0]['real']['per_window'], 30.0, 2)
        self.assertTrue(sugg[1]['real']['state'].startswith('not applied'))   # still xhigh
        self.assertTrue(sugg[2]['real']['state'].startswith('not applied'))   # still fable
        self.assertEqual(sugg[3]['real']['state'], 'no calls since the change')

    def test_too_early_and_wrong(self):
        side = lambda n, per, models: {'n': n, 'cost': n * per, 'per_call': per, 'models': models}
        cls = [{'class': 'code-explore', 'family': 'find_feature', 'saved': -0.5, 'check': None,
                'before': side(4, 0.5, {'claude-haiku-5-5': 4}), 'after': side(6, 0.6, {'claude-haiku-5-5': 6})}]
        main = {'before': {'msgs': 10, 'cost': 1, 'per_msg': 0.1}, 'after': {'msgs': 5, 'cost': 1, 'per_msg': 0.2}, 'saved': -0.5, 'rows': []}
        import unittest.mock as um
        sugg = [{'id': 'explore', 'saving': [20.0, 20.0]}]
        with um.patch.object(status, 'span_days', return_value=0.2):
            status.verdicts(sugg, self.latest(cls, main, '5 h'), 30)
        self.assertTrue(sugg[0]['real']['state'].startswith('too early'))
        sugg = [{'id': 'explore', 'saving': [20.0, 20.0]}]
        with um.patch.object(status, 'span_days', return_value=2.0):
            status.verdicts(sugg, self.latest(cls, main), 30)
        self.assertEqual(sugg[0]['real']['state'], 'wrong so far')


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

    def test_same_work_prices_the_after_tokens_at_the_before_model(self):
        tok = {'input_tokens': 20000, 'output_tokens': 1000, 'cache_read_input_tokens': 100000, 'cache_creation_input_tokens': 0}
        after = [{'cost': 0.01, 'tok': tok, 'model': 'claude-haiku-5-5'}]
        cf = status.price_tokens(tok, 'claude-opus-5-5')
        self.assertGreater(cf, 0.01)
        self.assertAlmostEqual(status.same_work(after, 'claude-opus-5-5'), round(cf - 0.01, 2), 2)
        self.assertIsNone(status.same_work(after, None))
        self.assertEqual(status.dominant({'claude-opus-5-5': 3, 'claude-haiku-5-5': 1, '?': 9}), 'claude-opus-5-5')

    def test_nothing_recorded(self):
        self.assertIsNone(status.realized_savings({'segments': None, 'subagents': {'calls': []}}, [], []))


if __name__ == '__main__':
    unittest.main()
