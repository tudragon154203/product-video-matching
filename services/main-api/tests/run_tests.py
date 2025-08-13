"""
Test runner for the main API service.
"""
import subprocess
import sys
import os


def run_tests():
    """Run all tests for the main API service."""
    print("Running all tests for the main API service...")
    
    # Run unit tests with pytest
    print("\n1. Running unit tests with pytest...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/test_main_api.py", "-v"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Unit tests failed!")
        return False
    
    # Run Ollama integration test
    print("\n2. Running Ollama integration test...")
    result = subprocess.run([
        sys.executable, "tests/test_ollama.py"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Ollama integration test failed!")
        return False
    
    print("\nAll tests passed!")
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)