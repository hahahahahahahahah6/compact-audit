import unittest
from compact_audit.audit import audit
from compact_audit.extract import extract


class AuditTests(unittest.TestCase):
    def test_basename(self):
        self.assertEqual(audit(extract(['Edited src/migrate.py']), 'migrate.py')['kept'], 1)

    def test_full_path(self):
        self.assertEqual(audit(extract(['Edited src/migrate.py']), 'src/migrate.py')['kept'], 1)

    def test_case_punctuation(self):
        self.assertEqual(audit(extract(['Decision: use SQLite!']), 'DECISION -- USE sqlite')['exit_code'], 0)

    def test_error_digits(self):
        self.assertEqual(audit(extract(['Error 123 at line 8']), 'Error 999 at line 42')['kept'], 1)

    def test_empty_summary(self):
        report = audit(extract(['Decision: use A', 'TODO work', 'Edited a.py']), '')
        self.assertEqual(report['dropped_count'], report['total_items'])
        self.assertEqual(report['exit_code'], 2)

    def test_empty_transcript(self):
        self.assertEqual(audit(extract([]), '')['exit_code'], 0)

    def test_warn(self):
        self.assertEqual(audit(extract(['TODO work']), '')['exit_code'], 1)

    def test_medium_threshold(self):
        self.assertEqual(audit(extract(['TODO work']), '', 'medium')['exit_code'], 2)

    def test_parse_errors_fail(self):
        self.assertEqual(audit(extract([], 1), '')['exit_code'], 2)

    def test_no_paraphrase(self):
        report = audit(extract(['Decision: use SQLite']), 'We chose an embedded SQL database')
        self.assertEqual(report['dropped_count'], 1)
        self.assertIn('verify manually', report['limitation'])

    def test_totals(self):
        report = audit(extract(['TODO one', 'TODO two']), 'TODO one')
        self.assertEqual(report['totals']['todo'], {'kept': 1, 'dropped': 1})
        self.assertEqual(len(report['totals']), 5)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            audit(extract([]), '', 'low')
