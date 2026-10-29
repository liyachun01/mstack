import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli
import proof
import project_state


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'example'
        with contextlib.redirect_stdout(io.StringIO()):
            cli.initialize(argparse.Namespace(path=self.project, name='example', preset='proof', model=None, context=[]))
        self.evidence = self.project / '.mstack/evidence/observed.json'
        self.evidence.parent.mkdir(parents=True)
        self.evidence.write_text('{"observed":true}')

    def record(self):
        for step in ('configuration', 'gstack', 'headroom', 'graphify', 'anytype', 'windmill'):
            proof.record(self.project, step, {'observed': True}, ['.mstack/evidence/observed.json'])

    def test_missing_live_receipts_fail(self):
        self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_complete_receipts_pass_and_artifact_tampering_fails(self):
        self.record()
        self.assertTrue(proof.inspect_proof(self.project)['passed'])
        self.evidence.write_text('{"observed":false}')
        self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_new_source_invalidates_old_proof(self):
        self.record()
        (self.project / 'src').mkdir()
        (self.project / 'src/app.py').write_text('raise RuntimeError("changed")')
        self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_binding_change_invalidates_proof(self):
        self.record()
        with project_state.edit(self.project) as state:
            state['bindings']['graphify'] = {'status':'changed'}
        self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_compact_daily_receipts_track_inherited_defaults(self):
        (self.project/'.mstack/stack.json').write_text('{"project":"example"}')
        fake_root=Path(self.temp.name)/'defaults'
        catalog=fake_root/'infra/stack/presets.json';catalog.parent.mkdir(parents=True)
        original=json.loads((proof.ROOT/'infra/stack/presets.json').read_text())
        catalog.write_text(json.dumps(original))
        with patch.object(proof,'ROOT',fake_root):
            self.record()
            self.assertTrue(proof.inspect_proof(self.project)['passed'])
            original['presets']['daily']['tools'].remove('graphify')
            catalog.write_text(json.dumps(original))
            self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_foreign_and_malformed_receipts_fail_closed(self):
        self.record()
        original = project_state.read(self.project)['proofs']['anytype']
        for value in ([], {**original, 'project': 'another-project'}):
            with project_state.edit(self.project) as state:
                state['proofs']['anytype'] = value
            self.assertFalse(proof.inspect_proof(self.project)['passed'])

    def test_evidence_path_escape_rejected(self):
        (self.project / 'outside.txt').write_text('unrelated')
        with self.assertRaises(ValueError):
            proof.record(self.project, 'anytype', {}, ['.mstack/evidence/../../outside.txt'])

    def test_nonproof_preset_cannot_claim_vacuous_success(self):
        p = self.project / '.mstack/stack.json'
        cfg = json.loads(p.read_text()); cfg['preset'] = 'solo'; p.write_text(json.dumps(cfg))
        self.assertFalse(proof.inspect_proof(self.project)['passed'])
