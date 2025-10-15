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

def main():
    """Run the collection phase happy path integration test"""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    test_file = script_dir / "integration" / "test_collection_phase_happy_path.py"
    
    if not test_file.exists():
        print(f"Error: Test file not found at {test_file}")
        sys.exit(1)
    
    # Change to the project root directory
    os.chdir(script_dir)
    
    # Run the test with pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        "integration/test_collection_phase_happy_path.py::TestCollectionPhaseHappyPath::test_collection_phase_happy_path_minimal_dataset",
        "-v",
        "--tb=short"
    ]
    
    print("Running Collection Phase Happy Path Integration Test...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
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