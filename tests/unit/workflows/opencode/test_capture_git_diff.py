from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def load_module() -> object:
    module_path = Path(__file__).resolve().parents[4] / ".github/workflows/scripts/bots/opencode/capture_git_diff.py"
    spec = importlib.util.spec_from_file_location("capture_git_diff", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load capture_git_diff module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


@contextmanager
def change_cwd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def init_repo(path: Path) -> None:
    git("init", cwd=path)
    git("config", "user.email", "test@example.com", cwd=path)
    git("config", "user.name", "Test User", cwd=path)


class CaptureGitDiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_capture_git_diff_includes_tracked_and_untracked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            init_repo(repo)

            tracked = repo / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            git("add", "tracked.txt", cwd=repo)
            git("commit", "-m", "initial", cwd=repo)

            tracked.write_text("hello\nworld\n", encoding="utf-8")
            (repo / "untracked.txt").write_text("new file\n", encoding="utf-8")

            diff_path = repo / "diff.patch"
            with change_cwd(repo):
                self.module.capture_git_diff(diff_path)  # type: ignore[attr-defined]

            content = diff_path.read_text(encoding="utf-8")
            self.assertIn("diff --git a/tracked.txt b/tracked.txt", content)
            self.assertIn("+++ b/untracked.txt", content)

    def test_capture_git_diff_appends_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            init_repo(repo)

            (repo / "file.txt").write_text("content\n", encoding="utf-8")
            git("add", "file.txt", cwd=repo)
            git("commit", "-m", "initial", cwd=repo)
            (repo / "file.txt").write_text("updated\n", encoding="utf-8")

            diff_path = repo / "diff.patch"
            env_path = repo / "env.out"
            with change_cwd(repo):
                self.module.capture_git_diff(diff_path)  # type: ignore[attr-defined]
                self.module.append_env_file(env_path, diff_path)  # type: ignore[attr-defined]

            env_content = env_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(env_content[-1], f"OPENCODE_GIT_DIFF_FILE={diff_path}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
