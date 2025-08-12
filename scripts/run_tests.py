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

# Add libs to path
sys.path.append(str(Path(__file__).parent.parent / 'infra'))

from config import config

def wait_for_services():
    """Wait for services to be ready"""
    # Get URLs from configuration
    main_api_url = config.MAIN_API_URL
    results_api_url = config.RESULTS_API_URL
    
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


def run_tests():
    """Run the integration tests"""
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Get URLs from configuration
    main_api_url = config.MAIN_API_URL
    results_api_url = config.RESULTS_API_URL
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        "POSTGRES_DSN": config.POSTGRES_DSN,
        "BUS_BROKER": config.BUS_BROKER,
        "MAIN_API_URL": main_api_url,
        "RESULTS_API_URL": results_api_url,
        "DATA_ROOT": config.DATA_ROOT,
        "EMBED_MODEL": config.EMBED_MODEL,
        "RETRIEVAL_TOPK": str(config.RETRIEVAL_TOPK),
        "SIM_DEEP_MIN": str(config.SIM_DEEP_MIN),
        "INLIERS_MIN": str(config.INLIERS_MIN),
        "MATCH_BEST_MIN": str(config.MATCH_BEST_MIN),
        "MATCH_CONS_MIN": str(config.MATCH_CONS_MIN),
        "MATCH_ACCEPT": str(config.MATCH_ACCEPT),
        "LOG_LEVEL": config.LOG_LEVEL,
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