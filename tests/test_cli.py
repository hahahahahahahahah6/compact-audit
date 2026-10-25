import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from compact_audit.cli import main

MIGRATION = 'Decision: migrations are forward-only; never roll back a shipped migration.'
FIXTURE = [MIGRATION, 'Edited src/migrate.py', 'Error: synthetic migration check failed with code 17']


class CliTests(unittest.TestCase):
    def invoke(self, transcript, summary, *options, suffix='.txt'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / ('transcript' + suffix)).write_text(transcript, encoding='utf-8')
            (path / 'summary.md').write_text(summary, encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['audit', str(path / ('transcript' + suffix)), str(path / 'summary.md'), *options])
            return code, output.getvalue()

    def test_full_coverage_exit_zero(self):
        self.assertEqual(self.invoke('\n'.join(FIXTURE), '\n'.join(FIXTURE))[0], 0)

    def test_migration_dropped(self):
        code, output = self.invoke('\n'.join(FIXTURE), '\n'.join(FIXTURE[1:]), '--json')
        report = json.loads(output)
        self.assertEqual(code, 2)
        self.assertTrue(any(x['category'] == 'decision' and x['severity'] == 'HIGH' for x in report['dropped']))

    def test_migration_kept_jsonl(self):
        transcript = '\n'.join(json.dumps({'content': line}) for line in FIXTURE)
        self.assertEqual(self.invoke(transcript, '\n'.join(FIXTURE), suffix='.jsonl')[0], 0)

    def test_warn_exit_one(self):
        self.assertEqual(self.invoke('TODO finish', '')[0], 1)

    def test_medium_exit_two(self):
        self.assertEqual(self.invoke('TODO finish', '', '--min-severity', 'medium')[0], 2)

    def test_malformed_exit_two(self):
        code, output = self.invoke('{bad\n{"content":"Decision: use A"}', 'Decision: use A', '--json', suffix='.jsonl')
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)['parse_errors'], 1)

    def test_json_valid_and_same_totals(self):
        code, output = self.invoke('TODO finish', '', '--json')
        report = json.loads(output)
        human_code, human = self.invoke('TODO finish', '')
        self.assertEqual(code, human_code)
        self.assertEqual(report['totals']['todo']['dropped'], 1)
        self.assertIn('todo: 0 kept, 1 dropped', human)
        self.assertIn('verify manually', human)

    def test_empty_transcript(self):
        self.assertEqual(self.invoke('', '', '--json')[0], 0)

    def test_empty_summary_all_dropped(self):
        _, output = self.invoke('\n'.join(FIXTURE), '', '--json')
        report = json.loads(output)
        self.assertEqual(report['total_items'], report['dropped_count'])

    def test_version(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            main(['--version'])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn('0.1.0', output.getvalue())

    def test_help(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['--help'])
        self.assertEqual(caught.exception.code, 0)

    def test_module(self):
        result = subprocess.run([sys.executable, '-m', 'compact_audit', '--version'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('0.1.0', result.stdout)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['audit', '/nonexistent-compact-audit-transcript', '/nonexistent-summary'])
        self.assertEqual(caught.exception.code, 2)
