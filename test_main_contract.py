import importlib.util
import os
from dataclasses import replace
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parent
MAIN = APP_ROOT / "main.py"

sys.path.insert(0, str(APP_ROOT))
SPEC = importlib.util.spec_from_file_location("xyz_main_under_test", MAIN)
MAIN_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MAIN_MODULE
SPEC.loader.exec_module(MAIN_MODULE)


class MainContractTests(unittest.TestCase):
    def _run_main(self, *args: str) -> tuple[int, str]:
        with patch("sys.stdout", new=StringIO()) as stdout:
            code = MAIN_MODULE.main(list(args))
        return code, stdout.getvalue()

    def test_no_args_matches_dash_h(self) -> None:
        no_args_code, no_args_output = self._run_main()
        help_code, help_output = self._run_main("-h")
        self.assertEqual(no_args_code, 0)
        self.assertEqual(help_code, 0)
        self.assertEqual(no_args_output, help_output)

    def test_help_is_human_written_and_unstyled(self) -> None:
        code, output = self._run_main("-h")
        self.assertEqual(code, 0)
        self.assertIn("xyz", output)
        self.assertIn("features:", output)
        self.assertIn("xyz conf", output)
        self.assertIn("xyz ls 10", output)
        self.assertNotIn("commands:", output)
        self.assertNotIn("usage:", output)
        self.assertNotIn("\x1b", output)

    def test_version_is_single_line(self) -> None:
        code, output = self._run_main("-v")
        self.assertEqual(code, 0)
        self.assertEqual(output, "0.0.0\n")

    def test_upgrade_invokes_install_script_with_dash_u(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            marker = temp_path / "install_args.txt"
            install_script = temp_path / "install.sh"
            install_script.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"${1:-}\" == \"-v\" ]]; then\n"
                "  printf '0.1.24\\n'\n"
                "  exit 0\n"
                "fi\n"
                "printf '%s\\n' \"$*\" > \"$XYZ_INSTALL_MARKER\"\n",
                encoding="utf-8",
            )
            install_script.chmod(0o755)

            patched_spec = replace(MAIN_MODULE.APP_SPEC, install_script_path=install_script)
            env = os.environ.copy()
            env["XYZ_INSTALL_MARKER"] = str(marker)
            with patch.dict(os.environ, env, clear=True), patch.object(
                MAIN_MODULE, "APP_SPEC", patched_spec
            ):
                code, _ = self._run_main("-u")

            self.assertEqual(code, 0)
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), "-u")

    def test_conf_creates_bootstrap_config_and_opens_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "EDITOR": "/usr/bin/true",
                    "XDG_CONFIG_HOME": str(temp_path / "config"),
                }
            )
            with patch.dict(os.environ, env, clear=True):
                code, _ = self._run_main("conf")

            self.assertEqual(code, 0)
            config_path = temp_path / "config" / "xyz" / "config.json"
            self.assertTrue(config_path.exists())
            self.assertEqual(
                config_path.read_text(encoding="utf-8"),
                MAIN_MODULE.CONFIG_BOOTSTRAP_TEXT,
            )

    def test_conf_rejects_extra_arguments(self) -> None:
        code, output = self._run_main("conf", "extra")
        self.assertEqual(code, 1)
        self.assertEqual(output, "Usage: xyz conf\n")


if __name__ == "__main__":
    unittest.main()
