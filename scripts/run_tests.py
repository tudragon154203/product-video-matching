#!/usr/bin/env python3
"""
Test runner script for integration tests
"""
import subprocess
import sys
import os
import time
import requests
from pathlib import Path


def wait_for_services():
    """Wait for services to be ready"""
    services = [
        ("Orchestrator", "http://localhost:8000/health"),
        ("Results API", "http://localhost:8080/health"),
        ("Vector Index", "http://localhost:8081/health")
    ]
    
    max_wait = 120  # 2 minutes
    wait_interval = 5
    
    print("Waiting for services to be ready...")
    
    for elapsed in range(0, max_wait, wait_interval):
        all_ready = True
        
        for service_name, health_url in services:
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service_name} is ready")
                else:
                    print(f"✗ {service_name} returned {response.status_code}")
                    all_ready = False
            except Exception as e:
                print(f"✗ {service_name} not ready: {e}")
                all_ready = False
        
        if all_ready:
            print("All services are ready!")
            return True
        
        if elapsed < max_wait - wait_interval:
            print(f"Waiting {wait_interval} more seconds...")
            time.sleep(wait_interval)
    
    print("Services did not become ready in time")
    return False


def run_tests():
    """Run the integration tests"""
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        "POSTGRES_DSN": "postgresql://postgres:dev@localhost:5432/postgres",
        "BUS_BROKER": "amqp://guest:guest@localhost:5672/",
        "ORCHESTRATOR_URL": "http://localhost:8000",
        "RESULTS_API_URL": "http://localhost:8080",
        "VECTOR_INDEX_URL": "http://localhost:8081"
    })
    
    # Wait for services
    if not wait_for_services():
        print("ERROR: Services not ready, cannot run tests")
        return 1
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--durations=10"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)