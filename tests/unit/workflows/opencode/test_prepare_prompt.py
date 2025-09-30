from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


def load_module() -> object:
    module_path = Path(__file__).resolve().parents[4] / ".github/workflows/scripts/bots/opencode/prepare_prompt.py"
    spec = importlib.util.spec_from_file_location("prepare_prompt", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load prepare_prompt module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


class GitDiffHintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_git_diff_hint_includes_path_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            diff_file = Path(tmp_dir) / "diff.patch"
            diff_file.write_text("diff --git a/file b/file\n", encoding="utf-8")
            os.environ["OPENCODE_GIT_DIFF_FILE"] = str(diff_file)
            try:
                hint = self.module._git_diff_hint()  # type: ignore[attr-defined]
            finally:
                os.environ.pop("OPENCODE_GIT_DIFF_FILE", None)
        self.assertIsNotNone(hint)
        self.assertIn(str(diff_file), hint)

    def test_git_diff_hint_returns_none_when_file_missing(self) -> None:
        os.environ["OPENCODE_GIT_DIFF_FILE"] = "/nonexistent/path.diff"
        try:
            hint = self.module._git_diff_hint()  # type: ignore[attr-defined]
        finally:
            os.environ.pop("OPENCODE_GIT_DIFF_FILE", None)
        self.assertIsNone(hint)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
