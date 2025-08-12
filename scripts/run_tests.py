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
    # Get URLs from environment variables or use defaults
    port_main = os.environ.get("PORT_MAIN", "8888")
    port_results = os.environ.get("PORT_RESULTS", "8890")
    
    main_api_url = os.environ.get("MAIN_API_URL", f"http://localhost:{port_main}")
    results_api_url = os.environ.get("RESULTS_API_URL", f"http://localhost:{port_results}")
    vector_index_url = os.environ.get("VECTOR_INDEX_URL", "http://localhost:8081")
    
    services = [
        ("Main API", f"{main_api_url}/health"),
        ("Results API", f"{results_api_url}/health")
        # Remove Vector Index health check since it's not exposed
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
                    print(f"+ {service_name} is ready")
                else:
                    print(f"x {service_name} returned {response.status_code}")
                    all_ready = False
            except Exception as e:
                print(f"x {service_name} not ready: {e}")
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
    
    # Get URLs from environment variables or use defaults
    port_main = os.environ.get("PORT_MAIN", "8888")
    port_results = os.environ.get("PORT_RESULTS", "8890")
    
    main_api_url = os.environ.get("MAIN_API_URL", f"http://localhost:{port_main}")
    results_api_url = os.environ.get("RESULTS_API_URL", f"http://localhost:{port_results}")
    vector_index_url = os.environ.get("VECTOR_INDEX_URL", "http://localhost:8081")
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        "POSTGRES_DSN": "postgresql://postgres:dev@localhost:5432/postgres",
        "BUS_BROKER": "amqp://guest:guest@localhost:5672/",
        "MAIN_API_URL": main_api_url,
        "RESULTS_API_URL": results_api_url,
        "VECTOR_INDEX_URL": vector_index_url
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