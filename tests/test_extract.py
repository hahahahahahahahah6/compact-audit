import tempfile
import unittest
from pathlib import Path
from compact_audit.extract import extract, normalize, read_transcript


class ExtractTests(unittest.TestCase):
    def test_decision_marker(self):
        self.assertEqual(extract(['DECISION: use sqlite']).items[0].category, 'decision')

    def test_decision_verbs(self):
        for phrase in ('decided to', 'we will use', 'chosen', 'agreed to', 'going with'):
            with self.subTest(phrase=phrase):
                self.assertEqual(extract([phrase + ' sqlite']).items[0].severity, 'HIGH')

    def test_constraints(self):
        for phrase in ('must not', 'never ', 'do not', 'must always', 'only ', 'required'):
            with self.subTest(phrase=phrase):
                item = extract([phrase + ' use sqlite']).items[0]
                self.assertEqual((item.category, item.severity), ('constraint', 'HIGH'))

    def test_only_requires_clause(self):
        self.assertEqual(extract(['only']).items, [])

    def test_errors(self):
        for phrase in ('Error: bad', 'Traceback', 'FAILED', 'failed with status', 'exit code 7', 'exit code: -2'):
            with self.subTest(phrase=phrase):
                item = extract([phrase]).items[0]
                self.assertEqual((item.category, item.severity), ('error', 'HIGH'))

    def test_zero_exit_is_not_error(self):
        self.assertEqual(extract(['exit code 0', 'exit code 00']).items, [])

    def test_error_numbers_stripped(self):
        self.assertEqual(extract(['Error 123 at line 8']).items[0].key, 'error at line')

    def test_file_extensions(self):
        for extension in ('py', 'js', 'ts', 'md', 'json', 'yaml', 'toml', 'go', 'rs'):
            with self.subTest(extension=extension):
                item = extract(['Edited lib/a.' + extension]).items[0]
                self.assertEqual((item.category, item.severity), ('file_edit', 'MEDIUM'))

    def test_special_directories(self):
        for directory in ('src', 'tests', 'docs'):
            self.assertEqual(extract(['Created ' + directory + '/Makefile']).items[0].category, 'file_edit')

    def test_edit_verbs(self):
        for verb in ('edited', 'changed', 'created', 'deleted', 'modified', 'wrote', 'rewrote', 'updated'):
            self.assertEqual(len(extract([verb + ' src/a.py']).items), 1)

    def test_path_without_edit(self):
        self.assertEqual(extract(['Read src/a.py']).items, [])

    def test_multiple_paths(self):
        self.assertEqual(len(extract(['Edited src/a.py and tests/b.py']).items), 2)

    def test_todos(self):
        for phrase in ('TODO', 'FIXME', 'not done', 'remaining', 'next step', 'still need'):
            self.assertEqual(extract([phrase + ' work']).items[0].severity, 'MEDIUM')

    def test_dedup(self):
        self.assertEqual(len(extract(['Decision: use A', 'DECISION -- use A', 'Decision: use A']).items), 1)

    def test_category_dedup_separate(self):
        self.assertEqual(len(extract(['Decision: must not roll back']).items), 2)

    def test_cap(self):
        result = extract(['TODO task ' + str(i) for i in range(502)])
        self.assertEqual(len(result.items), 500)
        self.assertTrue(result.truncated)
        self.assertEqual(result.items[-1].key, 'todo task 499')

    def test_exact_cap_not_truncated(self):
        self.assertFalse(extract(['TODO task ' + str(i) for i in range(500)]).truncated)

    def test_duplicates_beyond_cap(self):
        self.assertFalse(extract(['TODO task'] * 501).truncated)

    def test_source_truncated_key_full(self):
        item = extract(['Decision: ' + 'a' * 700]).items[0]
        self.assertEqual(len(item.text), 500)
        self.assertGreater(len(item.key), 500)

    def test_normalize(self):
        self.assertEqual(normalize(' A_b! C--D\t E '), 'a b c d e')

    def read(self, content, suffix):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ('input' + suffix)
            path.write_text(content, encoding='utf-8')
            return read_transcript(path)

    def test_json_fields(self):
        lines, errors = self.read('{"content":"one","text":"ignored"}\n{"text":"two"}\n{"message":"three"}', '.jsonl')
        self.assertEqual((lines, errors), (['one', 'two', 'three'], 0))

    def test_bad_json(self):
        self.assertEqual(self.read('{bad\n[]\n{"content":7}\n{}\n', '.jsonl'), ([], 3))

    def test_multiline_content(self):
        self.assertEqual(self.read('{"content":"a\\nb"}', '.jsonl'), (['a', 'b'], 0))

    def test_plain_lines(self):
        self.assertEqual(self.read('one\n\n two\n', '.md'), (['one', ' two'], 0))

    def test_empty(self):
        self.assertEqual(extract([]).items, [])
