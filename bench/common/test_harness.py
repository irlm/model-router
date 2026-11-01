"""Check that the adapters build the right command line and read the harness's
output into the shared receipt shape, without calling any harness.

Run: python3 bench/common/test_harness.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

CLAUDE = json.dumps({'result': 'ok', 'usage': {'input_tokens': 1}, 'total_cost_usd': 0.01, 'num_turns': 2,
                     'modelUsage': {'claude-x': {}}, 'permission_denials': []})
CODEX = '\n'.join(json.dumps(e) for e in [
    {'type': 'thread.started', 'thread_id': 't'},
    {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'ls', 'exit_code': 0}},
    {'type': 'item.completed', 'item': {'type': 'file_change', 'changes': [{'path': '/wt/lib/a.c', 'kind': 'update'}]}},
    {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok": true}'}},
    {'type': 'turn.completed', 'usage': {'input_tokens': 100, 'cached_input_tokens': 60, 'output_tokens': 5,
                                         'reasoning_output_tokens': 1}}])


def call(name, stdout, **kw):
    """Run the adapter with subprocess.run faked; return (argv, receipt)."""
    seen = []

    def fake_run(cmd, **_):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout, '')
    with mock.patch.object(harness.subprocess, 'run', side_effect=fake_run):
        r = harness.run(name, 'prompt', 'model-x', 'low', 3, 'Read Edit', 10, '/wt', **kw)
    return (seen[0] if seen else None), r


class Claude(unittest.TestCase):
    def test_plain(self):
        cmd, r = call('claude', CLAUDE)
        self.assertEqual((cmd[0], cmd[1]), (harness.CLAUDE, '-p'))   # argv[0] is the PATH lookup (claude.cmd on Windows)
        self.assertNotIn('--chrome', cmd)
        self.assertEqual(cmd[cmd.index('--allowed-tools') + 1], 'Read Edit')
        self.assertEqual((r['harness'], r['text'], r['num_turns'], r['model_used']), ('claude', 'ok', 2, 'claude-x'))
        self.assertIsNone(r['operational_error'])
        self.assertEqual(r['model_usage'], {'claude-x': {}})

    def test_chrome_and_ignored_keywords(self):
        cmd, _ = call('claude', CLAUDE, chrome=True, write=True, writable=['/b'], unsandboxed=True)
        self.assertEqual(cmd[2], '--chrome')
        self.assertFalse(any('/b' in c or 'danger' in c for c in cmd))

    def test_bad_output(self):
        _, r = call('claude', 'not json')
        self.assertEqual(r['operational_error'], 'invalid-endpoint-response')


class Codex(unittest.TestCase):
    def test_read_only(self):
        cmd, r = call('codex', CODEX)
        self.assertEqual(cmd[cmd.index('-s') + 1], 'read-only')
        self.assertFalse(any('writable_roots' in c for c in cmd))
        self.assertEqual(cmd[-1], '-')
        self.assertEqual(r['usage']['input_tokens'], 40)
        self.assertEqual(r['usage']['cache_read_input_tokens'], 60)
        self.assertEqual(r['text'], '{"ok": true}')
        self.assertEqual(r['commands'], [{'command': 'ls', 'exit_code': 0}])
        self.assertEqual(r['file_changes'], ['lib/a.c'])
        self.assertEqual(r['num_turns'], 3)
        self.assertEqual(r['sandbox'], 'read-only')
        self.assertIsNone(r['operational_error'])

    def test_write_with_roots(self):
        cmd, r = call('codex', CODEX, write=True, writable=['/b'])
        self.assertEqual(cmd[cmd.index('-s') + 1], 'workspace-write')
        self.assertIn('sandbox_workspace_write.writable_roots=["/b"]', cmd)
        self.assertIn('writable /b', r['harness_note'])

    def test_unsandboxed_drops_roots(self):
        cmd, r = call('codex', CODEX, write=True, writable=['/b'], unsandboxed=True)
        self.assertEqual(cmd[cmd.index('-s') + 1], 'danger-full-access')
        self.assertFalse(any('writable_roots' in c for c in cmd))
        self.assertEqual(r['sandbox'], 'danger-full-access')

    def test_no_browser(self):
        cmd, r = call('codex', CODEX, chrome=True)
        self.assertIsNone(cmd)
        self.assertEqual(r['operational_error'], 'harness-has-no-browser')

    def test_fatal(self):
        _, r = call('codex', json.dumps({'type': 'error', 'message': 'model not allowed'}))
        self.assertTrue(r['operational_error'].startswith('endpoint-error'))


class Capabilities(unittest.TestCase):
    def test_choices(self):
        self.assertEqual(harness.harnesses(('browser',)), ['claude'])
        self.assertEqual(harness.harnesses(('write',)), ['claude', 'codex'])
        self.assertEqual(harness.harnesses(), sorted(harness.ADAPTERS))


if __name__ == '__main__':
    unittest.main()
