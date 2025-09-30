#!/usr/bin/env python3
"""Capture repository diffs for the opencode workflow."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable


def _run_git_command(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the completed process."""
    return subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _list_untracked_files() -> list[str]:
    """Return a list of untracked files in the repository."""
    result = _run_git_command(["ls-files", "--others", "--exclude-standard", "-z"])
    output = result.stdout or ""
    if not output:
        return []
    return [path for path in output.split("\0") if path]


def _capture_tracked_diff() -> str:
    """Return the diff for tracked files."""
    result = _run_git_command(["diff"])
    return result.stdout or ""


def _capture_untracked_diff(path: str) -> str:
    """Return the diff for an untracked file."""
    result = _run_git_command(["diff", "--no-index", "--", "/dev/null", path])
    return result.stdout or ""


def capture_git_diff(diff_path: Path) -> None:
    """Capture tracked and untracked diffs into ``diff_path``."""
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    segments: list[str] = []

    tracked_diff = _capture_tracked_diff().rstrip("\n")
    if tracked_diff:
        segments.append(tracked_diff)

    for relative_path in _list_untracked_files():
        file_path = Path(relative_path)
        if not file_path.is_file():
            continue
        untracked_diff = _capture_untracked_diff(relative_path).rstrip("\n")
        if untracked_diff:
            segments.append(untracked_diff)

    if segments:
        diff_content = "\n\n".join(segments) + "\n"
    else:
        diff_content = ""

    diff_path.write_text(diff_content, encoding="utf-8")


def append_env_file(env_path: Path, diff_path: Path) -> None:
    """Append the environment variable declaration to ``env_path``."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    with env_path.open("a", encoding="utf-8") as handle:
        handle.write(f"OPENCODE_GIT_DIFF_FILE={diff_path}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff-file",
        required=True,
        help="Path where the repository diff will be written.",
    )
    parser.add_argument(
        "--env-file",
        help="Optional path to the GitHub Actions environment file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diff_path = Path(args.diff_file)
    capture_git_diff(diff_path)

    env_file = args.env_file
    if env_file:
        append_env_file(Path(env_file), diff_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
