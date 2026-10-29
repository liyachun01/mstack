"""Synthetic contract tests; no installed harness/vendor code is executed."""

import importlib.util
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "inspect_frontend", Path(__file__).parents[1] / "inspect_frontend.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SHELL = (
    'R.version="18.3.1";function seeds(){return{react:R,"react/jsx-runtime":J,'
    '"@deepseek-ai/dsh-client-ui-primitives":P}};boot({staticModules:seeds()})'
)
CLIENT = (
    'window.__ModuleLoader__.load({ id: "@anionex/dsh-vision-toolkit", '
    'factory: (require) => { require("react"); require("react/jsx-runtime"); '
    'require("@deepseek-ai/dsh-client-ui-primitives"); return {}; } });'
)


class BrowserContractTests(unittest.TestCase):
    def test_matching_seed_contract(self):
        result = audit.browser_contract(SHELL, CLIENT)
        self.assertTrue(result["all_imports_are_shell_seeds"])
        self.assertFalse(result["runtime_execution_tested"])
        self.assertEqual(len(result["required_browser_imports"]), 3)

    def test_seed_factory_must_be_used(self):
        with self.assertRaises(ValueError):
            audit.browser_contract(SHELL.replace("staticModules:seeds()", "unused:seeds()"), CLIENT)

    def test_unknown_external_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.browser_contract(SHELL, CLIENT.replace('require("react")', 'require("unknown")'))

    def test_factory_registration_required(self):
        with self.assertRaises(ValueError):
            audit.browser_contract(SHELL, CLIENT.replace("window.__ModuleLoader__", "other"))

    def test_version_drift_requires_review(self):
        with self.assertRaises(ValueError):
            audit.browser_contract(SHELL.replace("18.3.1", "18.2.0"), CLIENT)


if __name__ == "__main__":
    unittest.main()
