from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


@dataclass
class LintError:
    path: Path
    line_no: int
    column: int
    code: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line_no}:{self.column}: {self.code} {self.message}"


DEFAULT_MAX_LINE_LENGTH = 88


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ruff",
        description=(
            "Offline-compatible Ruff shim. Supports a subset of the actual "
            "Ruff command to keep codebases linted when the binary is not "
            "available."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path.cwd()],
        help="Files or directories to lint.",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=DEFAULT_MAX_LINE_LENGTH,
        help="Maximum allowed line length.",
    )
    return parser.parse_args(argv)


def iter_py_files(paths: Sequence[Path]) -> Iterator[Path]:
    for raw_path in paths:
        path = raw_path.resolve()
        if path.is_dir():
            yield from (
                child
                for child in path.rglob("*.py")
                if "__pycache__" not in child.parts and child.is_file()
            )
        elif path.is_file() and path.suffix == ".py":
            yield path


def lint_file(path: Path, max_line_length: int) -> Iterable[LintError]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive guard
        yield LintError(path, 1, 1, "E000", f"Unable to decode file: {exc}")
        return

    if not text.endswith("\n"):
        yield LintError(path, text.count("\n") + 1, 1, "W292", "no newline at end of file")

    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")
        if stripped.endswith(" "):
            column = len(stripped)
            yield LintError(path, index, column, "W291", "trailing whitespace")
        if "\t" in line:
            column = line.index("\t") + 1
            yield LintError(path, index, column, "W191", "tab indentation")
        if len(line) > max_line_length:
            yield LintError(
                path,
                index,
                max_line_length + 1,
                "E501",
                f"line too long ({len(line)} > {max_line_length})",
            )


def lint(paths: Sequence[Path], max_line_length: int) -> int:
    errors = list(lint_file(path, max_line_length) for path in iter_py_files(paths))
    flattened = [error for batch in errors for error in batch]
    for error in flattened:
        print(error.format())
    return 1 if flattened else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    exit_code = lint(args.paths, args.max_line_length)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
