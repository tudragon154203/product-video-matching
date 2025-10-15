#!/usr/bin/env python3
"""
Collection Phase Test Runner

Simple script to run the collection phase happy path integration test.
This provides a convenient way to execute the test without needing to remember the full pytest command.
"""
import sys
import subprocess
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TESTS_DIR.parent
LIBS_DIR = PROJECT_ROOT / "libs"
COMMON_PY_DIR = LIBS_DIR / "common-py"
TEST_FILE = TESTS_DIR / "integration" / "test_collection_phase_happy_path.py"

def build_env():
    """Ensure subprocess inherits shared library paths."""
    env = os.environ.copy()
    paths = [str(COMMON_PY_DIR), str(LIBS_DIR), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join([p for p in paths if p])
    return env

def main():
    """Run the collection phase happy path integration test"""
    if not TEST_FILE.exists():
        print(f"Error: Test file not found at {TEST_FILE.relative_to(PROJECT_ROOT)}")
        sys.exit(1)
    
    # Change to the project root directory
    os.chdir(PROJECT_ROOT)
    
    # Run the test with pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset",
        "-v",
        "--tb=short"
    ]
    
    print("Running Collection Phase Happy Path Integration Test...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, env=build_env())
        print("\n[SUCCESS] Collection phase test completed successfully!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n[FAILED] Collection phase test failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test interrupted by user")
        return 130

if __name__ == "__main__":
    sys.exit(main())
