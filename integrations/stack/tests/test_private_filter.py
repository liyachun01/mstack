import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import private_filter as pf


class PrivateFilterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.values = Path(temp.name)/'private.json'
        self.values.write_text(json.dumps({'values': {'USER': 'alice', 'REPO': 'acme', 'REPO_CAMEL': 'AcmeKit',
                                                      'EMPTY': ''}}))
        p = patch.object(pf, 'VALUES', self.values); p.start(); self.addCleanup(p.stop)

    def run_filter(self, mode, data):
        out = io.BytesIO()
        stdin = type('In', (), {'buffer': io.BytesIO(data)})()
        stdout = type('Out', (), {'buffer': out})()
        with patch.object(pf.sys, 'stdin', stdin), patch.object(pf.sys, 'stdout', stdout):
            self.assertEqual(pf.main([mode]), 0)
        return out.getvalue()

    def test_round_trip_and_longest_value_first(self):
        text = '/Users/alice/acme and AcmeKit and supabase_db_acme\n'.encode()
        clean = self.run_filter('clean', text)
        self.assertEqual(clean, b'/Users/{{mstack:USER}}/{{mstack:REPO}} and {{mstack:REPO_CAMEL}} and '
                                b'supabase_db_{{mstack:REPO}}\n')
        self.assertEqual(self.run_filter('smudge', clean), text)

    def test_binary_passes_through(self):
        blob = b'\x89PNG\x00\xffalice'
        self.assertEqual(self.run_filter('clean', blob), blob)

    def test_clean_refuses_without_values_and_smudge_keeps_placeholders(self):
        self.values.unlink()
        with self.assertRaises(SystemExit):
            self.run_filter('clean', b'alice')
        self.assertEqual(self.run_filter('smudge', b'{{mstack:USER}}'), b'{{mstack:USER}}')


if __name__ == '__main__':
    unittest.main()
