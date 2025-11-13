"""Shared pytest configuration for matcher service tests."""
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
SERVICE_ROOT = TESTS_DIR.parent
REPO_ROOT = SERVICE_ROOT.parent.parent
LIBS_ROOT = REPO_ROOT / "libs"
COMMON_PY_ROOT = LIBS_ROOT / "common-py"

for candidate in (SERVICE_ROOT, LIBS_ROOT, COMMON_PY_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)
