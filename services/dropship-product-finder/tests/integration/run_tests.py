#!/usr/bin/env python3
"""
Simple test runner for eBay integration tests.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_pytest_tests():
    """Run pytest tests with verbose output"""
    print("Running eBay integration tests with pytest...")
    
    # Change to the service directory
    service_dir = Path(__file__).parent.parent
    os.chdir(service_dir)
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/integration/test_ebay_collector_real2.py",
        "-v", "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running pytest: {e}")
        return False

def run_comprehensive_test():
    """Run the comprehensive test with JSON output"""
    print("Running comprehensive eBay integration test...")
    
    # Change to the service directory
    service_dir = Path(__file__).parent.parent
    os.chdir(service_dir)
    
    # Run comprehensive test
    cmd = [sys.executable, "tests/integration/test_ebay_collector_real2.py"]
    
    try:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running comprehensive test: {e}")
        return False

def run_specific_test(test_name):
    """Run a specific test function"""
    print(f"Running specific test: {test_name}")
    
    # Change to the service directory
    service_dir = Path(__file__).parent.parent
    os.chdir(service_dir)
    
    # Run specific test
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/integration/test_ebay_collector_real2.py::{test_name}",
        "-v", "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test {test_name}: {e}")
        return False

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "pytest":
            success = run_pytest_tests()
        elif command == "comprehensive":
            success = run_comprehensive_test()
        elif command == "specific":
            if len(sys.argv) < 3:
                print("Usage: python run_tests.py specific <test_name>")
                return 1
            test_name = sys.argv[2]
            success = run_specific_test(test_name)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: pytest, comprehensive, specific")
            return 1
    else:
        # Default: run pytest
        success = run_pytest_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())