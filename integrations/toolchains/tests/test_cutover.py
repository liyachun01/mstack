import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('cutover',Path(__file__).resolve().parents[1]/'cutover.py')
cutover=importlib.util.module_from_spec(spec);spec.loader.exec_module(cutover)

class ShellCutoverTests(unittest.TestCase):
    def test_preserves_unrelated_shell_and_removes_only_known_managers(self):
        original='export KEEP="private-value"\n'+cutover.FNM+'\n'+cutover.BUN+'\n. "$HOME/.local/bin/env"\n'
        result=cutover.transformed_shell(original)
        self.assertIn('export KEEP="private-value"',result)
        self.assertIn('. "$HOME/.local/bin/env"',result)
        self.assertNotIn('fnm env',result);self.assertNotIn('export BUN_INSTALL=',result)
        self.assertIn(str(cutover.BOOTSTRAP),result)
    def test_repeated_transform_is_identical(self):
        first=cutover.transformed_shell(cutover.FNM+cutover.BUN)
        self.assertEqual(cutover.transformed_shell(first),first)
    def test_unknown_activation_requires_review(self):
        with self.assertRaises(ValueError):cutover.transformed_shell('eval "$(fnm env --different)"\n')

if __name__=='__main__':unittest.main()
